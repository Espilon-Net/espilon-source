#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "esp_camera.h"
#include "esp_log.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <errno.h>
#include <ctype.h>

#include "command.h"
#include "utils.h"

/* ============================================================
 * CONFIG
 * ============================================================ */
#define TAG "CAMERA"
#define MAX_UDP_SIZE 2034

#if defined(CONFIG_RECON_MODE_CAMERA)
/* ================= CAMERA PINS ================= */
#define CAM_PIN_PWDN    32
#define CAM_PIN_RESET   -1
#define CAM_PIN_XCLK    0
#define CAM_PIN_SIOD    26
#define CAM_PIN_SIOC    27
#define CAM_PIN_D7      35
#define CAM_PIN_D6      34
#define CAM_PIN_D5      39
#define CAM_PIN_D4      36
#define CAM_PIN_D3      21
#define CAM_PIN_D2      19
#define CAM_PIN_D1      18
#define CAM_PIN_D0      5
#define CAM_PIN_VSYNC   25
#define CAM_PIN_HREF    23
#define CAM_PIN_PCLK    22

/* ============================================================
 * STATE
 * ============================================================ */
static volatile bool streaming_active = false;
static bool camera_initialized = false;

static int udp_sock = -1;
static struct sockaddr_in dest_addr;

/* ⚠️ à passer en Kconfig plus tard */
static const char *token = "Sup3rS3cretT0k3n";

/* ============================================================
 * CAMERA INIT
 * ============================================================ */
static bool init_camera(void)
{
    camera_config_t cfg = {
        .pin_pwdn       = CAM_PIN_PWDN,
        .pin_reset      = CAM_PIN_RESET,
        .pin_xclk       = CAM_PIN_XCLK,
        .pin_sccb_sda   = CAM_PIN_SIOD,
        .pin_sccb_scl   = CAM_PIN_SIOC,
        .pin_d7         = CAM_PIN_D7,
        .pin_d6         = CAM_PIN_D6,
        .pin_d5         = CAM_PIN_D5,
        .pin_d4         = CAM_PIN_D4,
        .pin_d3         = CAM_PIN_D3,
        .pin_d2         = CAM_PIN_D2,
        .pin_d1         = CAM_PIN_D1,
        .pin_d0         = CAM_PIN_D0,
        .pin_vsync      = CAM_PIN_VSYNC,
        .pin_href       = CAM_PIN_HREF,
        .pin_pclk       = CAM_PIN_PCLK,
        .xclk_freq_hz   = 20000000,
        .ledc_timer     = LEDC_TIMER_0,
        .ledc_channel   = LEDC_CHANNEL_0,
        .pixel_format   = PIXFORMAT_JPEG,
        .frame_size     = FRAMESIZE_QQVGA,
        .jpeg_quality   = 20,
        .fb_count       = 2,
        .fb_location    = CAMERA_FB_IN_PSRAM,
        .grab_mode      = CAMERA_GRAB_LATEST
    };

    if (esp_camera_init(&cfg) != ESP_OK) {
        msg_error(TAG, "camera init failed", NULL);
        return false;
    }

    msg_info(TAG, "camera initialized", NULL);
    vTaskDelay(pdMS_TO_TICKS(200));
    return true;
}

/* ============================================================
 * STREAM TASK
 * ============================================================ */
static void udp_stream_task(void *arg)
{
    (void)arg;

    msg_info(TAG, "stream started", NULL);

    const size_t token_len = strlen(token);
    uint8_t buf[MAX_UDP_SIZE + 32];
    uint32_t frame_count = 0;
    uint32_t error_count = 0;

    while (streaming_active) {

        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb) {
            msg_error(TAG, "frame capture failed", NULL);
            vTaskDelay(pdMS_TO_TICKS(50));
            continue;
        }

        frame_count++;
        size_t num_chunks = (fb->len + MAX_UDP_SIZE - 1) / MAX_UDP_SIZE;

        /* DEBUG: Log frame info every 10 frames */
        if (frame_count % 10 == 1) {
            ESP_LOGI(TAG, "frame #%lu: %u bytes, %u chunks, sock=%d",
                     frame_count, fb->len, num_chunks, udp_sock);
        }

        /* Check socket validity */
        if (udp_sock < 0) {
            ESP_LOGE(TAG, "socket invalid (sock=%d), stopping", udp_sock);
            esp_camera_fb_return(fb);
            break;
        }

        /* START */
        memcpy(buf, token, token_len);
        memcpy(buf + token_len, "START", 5);
        ssize_t ret = sendto(udp_sock, buf, token_len + 5, 0,
               (struct sockaddr *)&dest_addr, sizeof(dest_addr));
        if (ret < 0) {
            ESP_LOGE(TAG, "START send failed: errno=%d (%s)", errno, strerror(errno));
        }

        size_t off = 0;
        size_t rem = fb->len;
        size_t chunk_num = 0;

        while (rem > 0 && streaming_active) {
            size_t chunk = rem > MAX_UDP_SIZE ? MAX_UDP_SIZE : rem;

            memcpy(buf, token, token_len);
            memcpy(buf + token_len, fb->buf + off, chunk);

            ret = sendto(udp_sock, buf, token_len + chunk, 0,
                       (struct sockaddr *)&dest_addr,
                       sizeof(dest_addr));

            if (ret < 0) {
                error_count++;
                ESP_LOGE(TAG, "chunk %u/%u send failed: errno=%d (%s), errors=%lu",
                         chunk_num, num_chunks, errno, strerror(errno), error_count);

                /* Stop after too many consecutive errors */
                if (error_count > 50) {
                    ESP_LOGE(TAG, "too many errors, stopping stream");
                    streaming_active = false;
                }
                break;
            } else {
                error_count = 0; /* Reset on success */
            }

            off += chunk;
            rem -= chunk;
            chunk_num++;
            vTaskDelay(1);
        }

        /* END */
        memcpy(buf, token, token_len);
        memcpy(buf + token_len, "END", 3);
        ret = sendto(udp_sock, buf, token_len + 3, 0,
               (struct sockaddr *)&dest_addr, sizeof(dest_addr));
        if (ret < 0) {
            ESP_LOGE(TAG, "END send failed: errno=%d (%s)", errno, strerror(errno));
        }

        esp_camera_fb_return(fb);
        vTaskDelay(pdMS_TO_TICKS(140)); /* ~7 FPS */
    }

    if (udp_sock >= 0) {
        close(udp_sock);
        udp_sock = -1;
    }

    ESP_LOGI(TAG, "stream stopped after %lu frames", frame_count);
    msg_info(TAG, "stream stopped", NULL);
    vTaskDelete(NULL);
}

/* ============================================================
 * STREAM CONTROL
 * ============================================================ */
static void start_stream(const char *ip, uint16_t port)
{
    ESP_LOGI(TAG, "start_stream called: ip=%s port=%u", ip ? ip : "(null)", port);

    if (streaming_active) {
        msg_error(TAG, "stream already active", NULL);
        return;
    }

    if (!ip || ip[0] == '\0') {
        ESP_LOGE(TAG, "invalid IP: null/empty");
        msg_error(TAG, "invalid ip", NULL);
        return;
    }

    if (port == 0) {
        ESP_LOGE(TAG, "invalid port: 0");
        msg_error(TAG, "invalid port", NULL);
        return;
    }

    if (!camera_initialized) {
        ESP_LOGI(TAG, "initializing camera...");
        if (!init_camera()) {
            msg_error(TAG, "camera init failed", NULL);
            return;
        }
        camera_initialized = true;
    }

    // Create UDP socket
    udp_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    if (udp_sock < 0) {
        ESP_LOGE(TAG, "socket() failed: errno=%d (%s)", errno, strerror(errno));
        msg_error(TAG, "udp socket failed", NULL);
        return;
    }
    ESP_LOGI(TAG, "socket created: fd=%d", udp_sock);

    // Build destination address (use inet_pton instead of inet_addr)
    memset(&dest_addr, 0, sizeof(dest_addr));
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port   = htons(port);

    if (inet_pton(AF_INET, ip, &dest_addr.sin_addr) != 1) {
        ESP_LOGE(TAG, "invalid IP address: '%s'", ip);
        close(udp_sock);
        udp_sock = -1;
        msg_error(TAG, "invalid ip", NULL);
        return;
    }

    ESP_LOGI(TAG, "target: %s:%u (addr=0x%08x)",
             ip, port, (unsigned)dest_addr.sin_addr.s_addr);

    streaming_active = true;

    BaseType_t ret = xTaskCreatePinnedToCore(
        udp_stream_task,
        "cam_stream",
        8192,
        NULL,
        5,
        NULL,
        0
    );

    if (ret != pdPASS) {
        ESP_LOGE(TAG, "failed to create stream task");
        streaming_active = false;
        close(udp_sock);
        udp_sock = -1;
        msg_error(TAG, "task create failed", NULL);
        return;
    }
}


static void stop_stream(void)
{
    ESP_LOGI(TAG, "stop_stream called, active=%d", streaming_active);

    if (!streaming_active) {
        msg_error(TAG, "no active stream", NULL);
        return;
    }

    streaming_active = false;
    ESP_LOGI(TAG, "stream stop requested");
}

/* ============================================================
 * COMMAND HANDLERS
 * ============================================================ */
static int cmd_cam_start(int argc, char **argv, const char *req, void *ctx)
{
    (void)ctx;

    if (argc != 2) {
        msg_error(TAG, "usage: cam_start <ip> <port>", req);
        return -1;
    }

    // Copie défensive (au cas où argv pointe vers un buffer volatile)
    char ip[32] = {0};
    char port_s[32] = {0};
    strlcpy(ip, argv[0] ? argv[0] : "", sizeof(ip));
    strlcpy(port_s, argv[1] ? argv[1] : "", sizeof(port_s));

    // Trim espaces (début/fin) pour gérer "5000\r\n" etc.
    char *p = port_s;
    while (*p && isspace((unsigned char)*p)) p++;

    // Extraire uniquement les digits au début
    char digits[8] = {0}; // "65535" max
    size_t di = 0;
    while (*p && isdigit((unsigned char)*p) && di < sizeof(digits) - 1) {
        digits[di++] = *p++;
    }
    digits[di] = '\0';

    // Si aucun digit trouvé -> invalid
    if (di == 0) {
        ESP_LOGE(TAG, "invalid port (raw='%s')", port_s);
        // Dump hex pour debug (hyper utile)
        ESP_LOG_BUFFER_HEX(TAG, port_s, strnlen(port_s, sizeof(port_s)));
        msg_error(TAG, "invalid port", req);
        return -1;
    }

    unsigned long port_ul = strtoul(digits, NULL, 10);
    if (port_ul == 0 || port_ul > 65535) {
        ESP_LOGE(TAG, "invalid port value (digits='%s')", digits);
        msg_error(TAG, "invalid port", req);
        return -1;
    }
    uint16_t port = (uint16_t)port_ul;

    // IP check via inet_pton (robuste)
    struct in_addr addr;
    if (inet_pton(AF_INET, ip, &addr) != 1) {
        ESP_LOGE(TAG, "invalid IP address: '%s'", ip);
        msg_error(TAG, "invalid ip", req);
        return -1;
    }

    ESP_LOGI(TAG, "parsed: ip='%s' port=%u (raw_port='%s')", ip, port, port_s);
    start_stream(ip, port);
    return 0;
}



static int cmd_cam_stop(int argc,
                        char **argv,
                        const char *req,
                        void *ctx)
{
    (void)argc;
    (void)argv;
    (void)ctx;

    stop_stream();
    return 0;
}

/* ============================================================
 * REGISTER COMMANDS
 * ============================================================ */
static const command_t cmd_cam_start_def = {
    .name = "cam_start",
    .min_args = 2,
    .max_args = 2,
    .handler = cmd_cam_start,
    .ctx = NULL,
    .async = false
};

static const command_t cmd_cam_stop_def = {
    .name = "cam_stop",
    .min_args = 0,
    .max_args = 0,
    .handler = cmd_cam_stop,
    .ctx = NULL,
    .async = false
};

void mod_camera_register_commands(void)
{
    command_register(&cmd_cam_start_def);
    command_register(&cmd_cam_stop_def);
}

#endif