/*
 * cmd_network.c
 * Refactored for new command system (protobuf-based)
 */

 #include <stdlib.h>
 #include <string.h>
 #include <stdint.h>
 
 #include "esp_log.h"
 #include "freertos/FreeRTOS.h"
 #include "freertos/task.h"
 
 #include "command.h"
 #include "utils.h"
 
 /* ============================================================
  * EXTERNAL SYMBOLS
  * ============================================================ */
 int do_ping_cmd(int argc, char **argv);
 void arp_scan_task(void *pvParameters);
 void init_proxy(char *ip, int port);
 extern int proxy_running;
 void start_dos(const char *t_ip, uint16_t t_port, int count);
 
 #define TAG "CMD_NETWORK"
 
 /* ============================================================
  * COMMAND: ping <host> [...]
  * ============================================================ */
 static int cmd_ping(
     int argc,
     char **argv,
     const char *req,
     void *ctx
 ) {
     (void)ctx;
 
     if (argc < 1) {
         msg_error(TAG, "usage: ping <host> [...]", req);
         return -1;
     }
 
     return do_ping_cmd(argc + 1, argv - 1);
 }
 
 /* ============================================================
  * COMMAND: arp_scan
  * ============================================================ */
 static int cmd_arp_scan(
     int argc,
     char **argv,
     const char *req,
     void *ctx
 ) {
     (void)argc;
     (void)argv;
     (void)ctx;
     (void)req;
 
     xTaskCreatePinnedToCore(
         arp_scan_task,
         "arp_scan",
         6144,
         NULL,
         5,
         NULL,
         1
     );
 
     return 0;
 }
 
 /* ============================================================
  * COMMAND: proxy_start <ip> <port>
  * ============================================================ */
 static int cmd_proxy_start(
     int argc,
     char **argv,
     const char *req,
     void *ctx
 ) {
     (void)ctx;
 
     if (argc != 2) {
         msg_error(TAG, "usage: proxy_start <ip> <port>", req);
         return -1;
     }
 
     if (proxy_running) {
         msg_error(TAG, "proxy already running", req);
         return -1;
     }
 
     init_proxy(argv[0], atoi(argv[1]));
     msg_info(TAG, "proxy started", req);
     return 0;
 }
 
 /* ============================================================
  * COMMAND: proxy_stop
  * ============================================================ */
 static int cmd_proxy_stop(
     int argc,
     char **argv,
     const char *req,
     void *ctx
 ) {
     (void)argc;
     (void)argv;
     (void)ctx;
 
     if (!proxy_running) {
         msg_error(TAG, "proxy not running", req);
         return -1;
     }
 
     proxy_running = 0;
     msg_info(TAG, "proxy stopping", req);
     return 0;
 }
 
 /* ============================================================
  * COMMAND: dos_tcp <ip> <port> <count>
  * ============================================================ */
 static int cmd_dos_tcp(
     int argc,
     char **argv,
     const char *req,
     void *ctx
 ) {
     (void)ctx;
 
     if (argc != 3) {
         msg_error(TAG, "usage: dos_tcp <ip> <port> <count>", req);
         return -1;
     }
 
     start_dos(
         argv[0],
         (uint16_t)atoi(argv[1]),
         atoi(argv[2])
     );
 
     msg_info(TAG, "DOS task started", req);
     return 0;
 }
 
 /* ============================================================
  * REGISTER COMMANDS
  * ============================================================ */
 static const command_t network_cmds[] = {
     { "ping",        1, 8, cmd_ping,        NULL, true  },
     { "arp_scan",    0, 0, cmd_arp_scan,    NULL, true  },
     { "proxy_start", 2, 2, cmd_proxy_start, NULL, true  },
     { "proxy_stop",  0, 0, cmd_proxy_stop,  NULL, false },
     { "dos_tcp",     3, 3, cmd_dos_tcp,     NULL, true  }
 };
 
 void mod_network_register_commands(void)
 {
     for (size_t i = 0;
          i < sizeof(network_cmds) / sizeof(network_cmds[0]);
          i++) {
         command_register(&network_cmds[i]);
     }
 }
 