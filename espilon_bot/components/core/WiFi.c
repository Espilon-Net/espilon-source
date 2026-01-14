#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

#include "lwip/sockets.h"
#include "lwip/netdb.h"

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"

#include "c2.pb.h"
#include "pb_decode.h"

#include "utils.h"

int sock = -1;

#ifdef CONFIG_NETWORK_WIFI
static const char *TAG = "CORE_WIFI";



#define RX_BUF_SIZE          4096
#define RECONNECT_DELAY_MS   5000

/* =========================================================
 * WiFi init
 * ========================================================= */
void wifi_init(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = CONFIG_WIFI_SSID,
            .password = CONFIG_WIFI_PASS,
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_connect());

    ESP_LOGI(TAG, "Connecting to WiFi SSID=%s", CONFIG_WIFI_SSID);
}

/* =========================================================
 * TCP connect
 * ========================================================= */
static bool tcp_connect(void)
{
    struct sockaddr_in server_addr = {0};

    sock = lwip_socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        ESP_LOGE(TAG, "socket() failed");
        return false;
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(CONFIG_SERVER_PORT);
    server_addr.sin_addr.s_addr = inet_addr(CONFIG_SERVER_IP);

    if (lwip_connect(sock,
                     (struct sockaddr *)&server_addr,
                     sizeof(server_addr)) != 0) {
        ESP_LOGE(TAG, "connect() failed");
        lwip_close(sock);
        sock = -1;
        return false;
    }

    ESP_LOGI(TAG, "Connected to %s:%d",
             CONFIG_SERVER_IP,
             CONFIG_SERVER_PORT);
    return true;
}


/* =========================================================
 * Handle incoming frame
 * ========================================================= */
static void handle_frame(const uint8_t *buf, size_t len)
{
    char tmp[len + 1];
    memcpy(tmp, buf, len);
    tmp[len] = '\0';
    c2_decode_and_exec(tmp);
}


/* =========================================================
 * TCP RX loop
 * ========================================================= */
static void tcp_rx_loop(void)
{
    static uint8_t rx_buf[RX_BUF_SIZE];

    int len = lwip_recv(sock, rx_buf, sizeof(rx_buf) - 1, 0);
    if (len <= 0) {
        ESP_LOGW(TAG, "RX failed / disconnected");
        lwip_close(sock);
        sock = -1;
        return;
    }

    /* IMPORTANT: string termination for strtok */
    rx_buf[len] = '\0';

    char *line = strtok((char *)rx_buf, "\n");
    while (line) {
        handle_frame((uint8_t *)line, strlen(line));
        line = strtok(NULL, "\n");
    }
}

/* =========================================================
 * Main TCP client task
 * ========================================================= */
void tcp_client_task(void *pvParameters)
{
    while (1) {

        if (!tcp_connect()) {
            vTaskDelay(pdMS_TO_TICKS(RECONNECT_DELAY_MS));
            continue;
        }
        msg_info(TAG, CONFIG_DEVICE_ID, NULL);
        ESP_LOGI(TAG, "Handshake done");

        while (sock >= 0) {
            tcp_rx_loop();
            vTaskDelay(1);
        }

        ESP_LOGW(TAG, "Disconnected, retrying...");
        vTaskDelay(pdMS_TO_TICKS(RECONNECT_DELAY_MS));
    }
}

#endif /* CONFIG_NETWORK_WIFI */