#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "sdkconfig.h"
#include "esp_log.h"

/* >>> CRITIQUE <<< */
#include "c2.pb.h"   /* c2_Command, c2_AgentMsgType */

/* ============================================================
 * GLOBAL DEFINES
 * ============================================================ */

#define MAX_ARGS           10
#define MAX_RESPONSE_SIZE  1024

/* Socket TCP global */
extern int sock;

/* ============================================================
 * COM INIT
 * ============================================================ */

bool com_init(void);

/* ============================================================
 * CRYPTO API
 * ============================================================ */

/*
 * ChaCha20 encrypt/decrypt
 * Retourne un buffer malloc()'d → free() obligatoire
 */
unsigned char *chacha_cd(const unsigned char *data, size_t data_len);

/* Base64 helpers */
char *base64_decode(const char *input, size_t *output_len);
char *base64_encode(const unsigned char *input, size_t input_len);

/* C2 decode + decrypt + protobuf + exec */
bool c2_decode_and_exec(const char *frame);
/* ============================================================
 * ESP → C2 Messaging API
 * ============================================================ */

bool agent_send(
    c2_AgentMsgType type,
    const char *source,
    const char *request_id,
    const void *data,
    size_t len,
    bool eof
);

/* Helpers globaux */
bool msg_info(
    const char *src,
    const char *msg,
    const char *req
);

bool msg_error(
    const char *src,
    const char *msg,
    const char *req
);

bool msg_data(
    const char *src,
    const void *data,
    size_t len,
    bool eof,
    const char *req
);

/* ============================================================
 * DEVICE
 * ============================================================ */

bool device_id_matches(
    const char *local_id,
    const char *target_id
);

/* ============================================================
 * CORE PROCESSING (C2 → ESP)
 * ============================================================ */

void process_command(
    const c2_Command *cmd
);

/*
 * Compat legacy optionnel
 */
void process_command_from_buffer(
    uint8_t *buffer,
    size_t len
);

/* ============================================================
 * WIFI
 * ============================================================ */
#ifdef CONFIG_NETWORK_WIFI
void wifi_init(void);
void tcp_client_task(void *pvParameters);
#endif

/* ============================================================
 * GPRS
 * ============================================================ */

#ifdef CONFIG_NETWORK_GPRS
#define BUFF_SIZE 1024
#define UART_NUM UART_NUM_1
#define TXD_PIN  27
#define RXD_PIN  26
#define PWR_KEY  4
#define PWR_EN   23
#define RESET    5
#define LED_GPIO 13

void setup_uart(void);
void setup_modem(void);

bool connect_gprs(void);
bool connect_tcp(void);

bool gprs_send(const void *buf, size_t len);
void gprs_rx_poll(void);
void close_tcp_connection(void);

void gprs_client_task(void *pvParameters);
void send_at_command(const char *cmd);
#endif


#ifdef __cplusplus
}
#endif
