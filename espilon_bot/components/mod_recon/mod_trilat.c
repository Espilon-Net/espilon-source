#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#include "esp_log.h"
#include "esp_err.h"
#include "nvs_flash.h"

#include "esp_bt.h"
#include "esp_gap_ble_api.h"
#include "esp_bt_main.h"

#include "esp_http_client.h"

#include "command.h"
#include "utils.h"

/* ============================================================
 * CONFIG
 * ============================================================ */
#define TAG "BLE_TRILAT"

#define TRILAT_ID "ESP3"
#define X_POS 10.0
#define Y_POS 0.0

#define MAX_BUFFER_SIZE 4096
#define POST_INTERVAL_MS 10000
#define MAX_LEN 128

/* ============================================================
 * STATE
 * ============================================================ */
static uint8_t target_mac[6];
static char target_url[MAX_LEN];
static char auth_bearer[MAX_LEN];
static char auth_header[MAX_LEN];

static char data_buffer[MAX_BUFFER_SIZE];
static size_t buffer_len = 0;

static SemaphoreHandle_t buffer_mutex = NULL;
static TaskHandle_t post_task_handle = NULL;
static bool trilat_running = false;

/* ============================================================
 * UTILS
 * ============================================================ */
static bool parse_mac_str(const char *input, uint8_t *mac_out)
{
    char clean[13] = {0};
    int j = 0;

    for (int i = 0; input[i] && j < 12; i++) {
        if (input[i] == ':' || input[i] == '-' || input[i] == ' ')
            continue;
        if (!isxdigit((unsigned char)input[i]))
            return false;
        clean[j++] = toupper((unsigned char)input[i]);
    }

    if (j != 12) return false;

    for (int i = 0; i < 6; i++) {
        char b[3] = { clean[i*2], clean[i*2+1], 0 };
        mac_out[i] = (uint8_t)strtol(b, NULL, 16);
    }
    return true;
}

/* ============================================================
 * HTTP
 * ============================================================ */
static esp_err_t http_evt(esp_http_client_event_t *evt)
{
    return ESP_OK;
}

static void send_http_post(const char *data)
{
    esp_http_client_config_t cfg = {
        .url = target_url,
        .timeout_ms = 10000,
        .event_handler = http_evt,
    };

    esp_http_client_handle_t cli = esp_http_client_init(&cfg);
    esp_http_client_set_method(cli, HTTP_METHOD_POST);
    esp_http_client_set_header(cli, "Content-Type", "text/plain");
    esp_http_client_set_header(cli, "Authorization", auth_header);
    esp_http_client_set_post_field(cli, data, strlen(data));

    esp_err_t err = esp_http_client_perform(cli);
    if (err == ESP_OK) {
        msg_info(TAG, "HTTP POST sent", NULL);
    } else {
        msg_error(TAG, "HTTP POST failed", NULL);
    }

    esp_http_client_cleanup(cli);
}

/* ============================================================
 * BLE CALLBACK
 * ============================================================ */
static void ble_scan_cb(esp_gap_ble_cb_event_t event,
                        esp_ble_gap_cb_param_t *param)
{
    if (!trilat_running) return;

    if (event != ESP_GAP_BLE_SCAN_RESULT_EVT ||
        param->scan_rst.search_evt != ESP_GAP_SEARCH_INQ_RES_EVT)
        return;

    if (memcmp(param->scan_rst.bda, target_mac, 6) != 0)
        return;

    char line[96];
    snprintf(line, sizeof(line),
             "%s;(%.1f,%.1f);%d\n",
             TRILAT_ID, X_POS, Y_POS,
             param->scan_rst.rssi);

    xSemaphoreTake(buffer_mutex, portMAX_DELAY);
    if (buffer_len + strlen(line) < MAX_BUFFER_SIZE) {
        strcat(data_buffer, line);
        buffer_len += strlen(line);
    }
    xSemaphoreGive(buffer_mutex);
}

/* ============================================================
 * POST TASK
 * ============================================================ */
static void post_task(void *arg)
{
    while (trilat_running) {
        vTaskDelay(pdMS_TO_TICKS(POST_INTERVAL_MS));

        xSemaphoreTake(buffer_mutex, portMAX_DELAY);
        if (buffer_len > 0) {
            send_http_post(data_buffer);
            buffer_len = 0;
            data_buffer[0] = 0;
        }
        xSemaphoreGive(buffer_mutex);
    }

    vTaskDelete(NULL);
}

/* ============================================================
 * BLE INIT
 * ============================================================ */
static void ble_init(void)
{
    esp_bt_controller_config_t cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();

    ESP_ERROR_CHECK(esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT));
    ESP_ERROR_CHECK(esp_bt_controller_init(&cfg));
    ESP_ERROR_CHECK(esp_bt_controller_enable(ESP_BT_MODE_BLE));
    ESP_ERROR_CHECK(esp_bluedroid_init());
    ESP_ERROR_CHECK(esp_bluedroid_enable());

    ESP_ERROR_CHECK(esp_ble_gap_register_callback(ble_scan_cb));

    esp_ble_scan_params_t scan = {
        .scan_type = BLE_SCAN_TYPE_ACTIVE,
        .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
        .scan_filter_policy = BLE_SCAN_FILTER_ALLOW_ALL,
        .scan_interval = 0x50,
        .scan_window = 0x30,
        .scan_duplicate = BLE_SCAN_DUPLICATE_DISABLE
    };

    ESP_ERROR_CHECK(esp_ble_gap_set_scan_params(&scan));
}

/* ============================================================
 * COMMANDS
 * ============================================================ */
static esp_err_t cmd_trilat_start(int argc, char **argv, void *ctx)
{
    if (argc != 4)
        return msg_error(TAG, "usage: trilat start <mac> <url> <bearer>", NULL);

    if (trilat_running)
        return msg_error(TAG, "already running", NULL);

    ESP_ERROR_CHECK(nvs_flash_init());

    if (!parse_mac_str(argv[1], target_mac))
        return msg_error(TAG, "invalid MAC", NULL);

    strncpy(target_url, argv[2], MAX_LEN-1);
    strncpy(auth_bearer, argv[3], MAX_LEN-1);
    snprintf(auth_header, sizeof(auth_header), "Bearer %s", auth_bearer);

    buffer_mutex = xSemaphoreCreateMutex();
    data_buffer[0] = 0;
    buffer_len = 0;

    ble_init();
    esp_ble_gap_start_scanning(0);

    trilat_running = true;
    xTaskCreate(post_task, "trilat_post", 4096, NULL, 5, &post_task_handle);

    msg_info(TAG, "trilat started", NULL);
    return ESP_OK;
}

static esp_err_t cmd_trilat_stop(int argc, char **argv, void *ctx)
{
    if (!trilat_running)
        return msg_error(TAG, "not running", NULL);

    trilat_running = false;
    esp_ble_gap_stop_scanning();

    msg_info(TAG, "trilat stopped", NULL);
    return ESP_OK;
}

/* ============================================================
 * REGISTER
 * ============================================================ */
static const command_t cmd_trilat_start_def = {
    .name = "trilat",
    .sub  = "start",
    .help = "Start BLE trilateration",
    .handler = cmd_trilat_start,
    .ctx = NULL,
    .async = false,
    .min_args = 4,
    .max_args = 4
};

static const command_t cmd_trilat_stop_def = {
    .name = "trilat",
    .sub  = "stop",
    .help = "Stop BLE trilateration",
    .handler = cmd_trilat_stop,
    .ctx = NULL,
    .async = false,
    .min_args = 2,
    .max_args = 2
};

void mod_ble_trilat_register_commands(void)
{
    command_register(&cmd_trilat_start_def);
    command_register(&cmd_trilat_stop_def);
}
