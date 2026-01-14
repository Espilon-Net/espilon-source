#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "lwip/lwip_napt.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#include "fakeAP_utils.h"
#include "utils.h"

static const char *TAG = "MODULE_FAKE_AP";

/* ================= AUTH ================= */
ip4_addr_t authenticated_clients[MAX_CLIENTS];  /* exported for mod_web_server.c */
int authenticated_count = 0;                     /* exported for mod_web_server.c */
static SemaphoreHandle_t auth_mutex;

/* ================= DNS ================= */
static TaskHandle_t dns_task_handle = NULL;

typedef struct {
    bool captive_portal;
} dns_param_t;

/* Forward declaration */
void dns_forwarder_task(void *pv);

/* ============================================================
 * AUTH
 * ============================================================ */
bool fakeap_is_authenticated(ip4_addr_t ip)
{
    bool res = false;
    xSemaphoreTake(auth_mutex, portMAX_DELAY);
    for (int i = 0; i < authenticated_count; i++) {
        if (authenticated_clients[i].addr == ip.addr) {
            res = true;
            break;
        }
    }
    xSemaphoreGive(auth_mutex);
    return res;
}

void fakeap_mark_authenticated(ip4_addr_t ip)
{
    xSemaphoreTake(auth_mutex, portMAX_DELAY);
    if (authenticated_count < MAX_CLIENTS) {
        authenticated_clients[authenticated_count++] = ip;
        ESP_LOGI(TAG, "Client authenticated: %s", ip4addr_ntoa(&ip));
    }
    xSemaphoreGive(auth_mutex);
}

static void fakeap_reset_auth(void)
{
    xSemaphoreTake(auth_mutex, portMAX_DELAY);
    authenticated_count = 0;
    memset(authenticated_clients, 0, sizeof(authenticated_clients));
    xSemaphoreGive(auth_mutex);
}

/* ============================================================
 * AP
 * ============================================================ */
void stop_access_point(void)
{
    if (dns_task_handle) {
        vTaskDelete(dns_task_handle);
        dns_task_handle = NULL;
    }
    fakeap_reset_auth();
    esp_wifi_set_mode(WIFI_MODE_STA);
    msg_info(TAG, "Access Point stopped", NULL);
}

void start_access_point(const char *ssid, const char *password, bool open)
{
    if (!auth_mutex)
        auth_mutex = xSemaphoreCreateMutex();

    fakeap_reset_auth();

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));

    wifi_config_t cfg = {0};
    strncpy((char *)cfg.ap.ssid, ssid, sizeof(cfg.ap.ssid));
    cfg.ap.ssid_len = strlen(ssid);
    cfg.ap.max_connection = MAX_CLIENTS;

    if (open) {
        cfg.ap.authmode = WIFI_AUTH_OPEN;
    } else {
        strncpy((char *)cfg.ap.password, password, sizeof(cfg.ap.password));
        cfg.ap.authmode = WIFI_AUTH_WPA_WPA2_PSK;
    }

    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &cfg));
    vTaskDelay(pdMS_TO_TICKS(2000));

    esp_netif_t *ap = esp_netif_get_handle_from_ifkey("WIFI_AP_DEF");
    esp_netif_ip_info_t ip;
    esp_netif_get_ip_info(ap, &ip);

    esp_netif_dhcps_stop(ap);
    esp_netif_dhcps_option(
        ap,
        ESP_NETIF_OP_SET,
        ESP_NETIF_DOMAIN_NAME_SERVER,
        &ip.ip,
        sizeof(ip.ip)
    );
    esp_netif_dhcps_start(ap);

    ip_napt_enable(ip.ip.addr, 1);

    dns_param_t *p = calloc(1, sizeof(*p));
    p->captive_portal = open;

    xTaskCreate(
        dns_forwarder_task,
        "dns_forwarder",
        4096,
        p,
        5,
        &dns_task_handle
    );

    char msg[64];
    snprintf(msg, sizeof(msg), "FakeAP started (%s)", open ? "captive" : "open");
    msg_info(TAG, msg, NULL);
}

/* ============================================================
 * DNS
 * ============================================================ */
static void send_dns_spoof(
    int sock,
    struct sockaddr_in *cli,
    socklen_t len,
    uint8_t *req,
    int req_len,
    uint32_t ip
) {
    uint8_t resp[512];
    memcpy(resp, req, req_len);

    resp[2] |= 0x80;      // QR = response
    resp[3] |= 0x80;      // RA
    resp[7] = 1;          // ANCOUNT

    int off = req_len;
    resp[off++] = 0xC0; resp[off++] = 0x0C;
    resp[off++] = 0x00; resp[off++] = 0x01;
    resp[off++] = 0x00; resp[off++] = 0x01;
    resp[off++] = 0; resp[off++] = 0; resp[off++] = 0; resp[off++] = 30;
    resp[off++] = 0; resp[off++] = 4;
    memcpy(&resp[off], &ip, 4);
    off += 4;

    sendto(sock, resp, off, 0, (struct sockaddr *)cli, len);
}

void dns_forwarder_task(void *pv)
{
    dns_param_t *p = pv;
    bool captive = p->captive_portal;
    free(p);

    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);

    struct sockaddr_in local = {
        .sin_family = AF_INET,
        .sin_port = htons(DNS_PORT),
        .sin_addr.s_addr = htonl(INADDR_ANY)
    };
    bind(sock, (struct sockaddr *)&local, sizeof(local));

    char msg[64];
    snprintf(msg, sizeof(msg), "DNS forwarder running (captive=%d)", captive);
    msg_info(TAG, msg, NULL);

    uint8_t buf[512];
    while (1) {
        struct sockaddr_in cli;
        socklen_t l = sizeof(cli);
        int r = recvfrom(sock, buf, sizeof(buf), 0,
                         (struct sockaddr *)&cli, &l);
        if (r <= 0) continue;

        ip4_addr_t ip;
        ip.addr = cli.sin_addr.s_addr;

        if (captive && !fakeap_is_authenticated(ip)) {
            send_dns_spoof(sock, &cli, l, buf, r, inet_addr(CAPTIVE_PORTAL_IP));
            continue;
        }

        int up = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        struct sockaddr_in dns = {
            .sin_family = AF_INET,
            .sin_port = htons(53),
            .sin_addr.s_addr = inet_addr(UPSTREAM_DNS)
        };

        sendto(up, buf, r, 0, (struct sockaddr *)&dns, sizeof(dns));
        r = recvfrom(up, buf, sizeof(buf), 0, NULL, NULL);
        if (r > 0)
            sendto(sock, buf, r, 0, (struct sockaddr *)&cli, l);
        close(up);
    }
}
