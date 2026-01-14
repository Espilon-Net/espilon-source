/*
 * Eun0us - ICMP Ping Module
 * Clean & stream-based implementation
 */

 #include <stdio.h>
 #include <string.h>
 #include <stdlib.h>
 
 #include "lwip/inet.h"
 #include "lwip/netdb.h"
 #include "esp_log.h"
 #include "ping/ping_sock.h"
 
 #include "utils.h"
 
 #define TAG "PING"
 
 static char line[256];
 
 /* ============================================================
  * Ping callbacks
  * ============================================================ */
 
 static void ping_on_success(esp_ping_handle_t hdl, void *args)
 {
     (void)args;
 
     uint8_t ttl;
     uint16_t seq;
     uint32_t time_ms, size;
     ip_addr_t addr;
 
     esp_ping_get_profile(hdl, ESP_PING_PROF_SEQNO,   &seq,     sizeof(seq));
     esp_ping_get_profile(hdl, ESP_PING_PROF_TTL,     &ttl,     sizeof(ttl));
     esp_ping_get_profile(hdl, ESP_PING_PROF_TIMEGAP, &time_ms, sizeof(time_ms));
     esp_ping_get_profile(hdl, ESP_PING_PROF_SIZE,    &size,    sizeof(size));
     esp_ping_get_profile(hdl, ESP_PING_PROF_IPADDR,  &addr,    sizeof(addr));
 
     int len = snprintf(line, sizeof(line),
         "%lu bytes from %s: icmp_seq=%u ttl=%u time=%lums",
         (unsigned long)size,
         ipaddr_ntoa(&addr),
         seq,
         ttl,
         (unsigned long)time_ms
     );
 
     if (len > 0) {
         msg_data(TAG, line, len,  false, NULL);
     }
 }
 
 static void ping_on_timeout(esp_ping_handle_t hdl, void *args)
 {
     (void)args;
 
     uint16_t seq;
     ip_addr_t addr;
 
     esp_ping_get_profile(hdl, ESP_PING_PROF_SEQNO,  &seq,  sizeof(seq));
     esp_ping_get_profile(hdl, ESP_PING_PROF_IPADDR, &addr, sizeof(addr));
 
     int len = snprintf(line, sizeof(line),
         "From %s: icmp_seq=%u timeout",
         ipaddr_ntoa(&addr),
         seq
     );
 
     if (len > 0) {
         msg_data(TAG, line, len, false, NULL);
     }
 }
 
 static void ping_on_end(esp_ping_handle_t hdl, void *args)
 {
     (void)args;
 
     uint32_t sent, recv, duration;
     ip_addr_t addr;
 
     esp_ping_get_profile(hdl, ESP_PING_PROF_REQUEST,  &sent,     sizeof(sent));
     esp_ping_get_profile(hdl, ESP_PING_PROF_REPLY,    &recv,     sizeof(recv));
     esp_ping_get_profile(hdl, ESP_PING_PROF_DURATION, &duration, sizeof(duration));
     esp_ping_get_profile(hdl, ESP_PING_PROF_IPADDR,   &addr,     sizeof(addr));
 
     int loss = sent ? (100 - (recv * 100 / sent)) : 0;
 
     int len = snprintf(line, sizeof(line),
         "--- %s ping statistics ---\n"
         "%lu packets transmitted, %lu received, %d%% packet loss, time %lums",
         ipaddr_ntoa(&addr),
         (unsigned long)sent,
         (unsigned long)recv,
         loss,
         (unsigned long)duration
     );
 
     if (len > 0) {
         /* Final summary, end of stream */
         msg_data(TAG, line, len, true, NULL);

     }
 
     esp_ping_delete_session(hdl);
 }
 
 /* ============================================================
  * Command entry point (used by network command wrapper)
  * ============================================================ */
 
 int do_ping_cmd(int argc, char **argv)
 {
     if (argc < 2) {
         msg_error(TAG,
             "usage: ping <host> [timeout interval size count ttl iface]",
             NULL);
         return -1;
     }
 
     esp_ping_config_t cfg = ESP_PING_DEFAULT_CONFIG();
     cfg.count = 4;
     cfg.timeout_ms = 1000;
 
     const char *host = argv[1];
 
     /* Optional arguments */
     if (argc > 2) cfg.timeout_ms  = atoi(argv[2]) * 1000;
     if (argc > 3) cfg.interval_ms = (uint32_t)(atof(argv[3]) * 1000);
     if (argc > 4) cfg.data_size   = atoi(argv[4]);
     if (argc > 5) cfg.count       = atoi(argv[5]);
     if (argc > 6) cfg.tos         = atoi(argv[6]);
     if (argc > 7) cfg.ttl         = atoi(argv[7]);
 
     /* Resolve host */
     ip_addr_t target;
     memset(&target, 0, sizeof(target));
 
     if (!ipaddr_aton(host, &target)) {
         struct addrinfo *res = NULL;
 
         if (getaddrinfo(host, NULL, NULL, &res) != 0 || !res) {
             msg_error(TAG, "unknown host", NULL);
             return -1;
         }
 
 #ifdef CONFIG_LWIP_IPV4
         if (res->ai_family == AF_INET) {
             inet_addr_to_ip4addr(
                 ip_2_ip4(&target),
                 &((struct sockaddr_in *)res->ai_addr)->sin_addr
             );
         }
 #endif
 
 #ifdef CONFIG_LWIP_IPV6
         if (res->ai_family == AF_INET6) {
             inet6_addr_to_ip6addr(
                 ip_2_ip6(&target),
                 &((struct sockaddr_in6 *)res->ai_addr)->sin6_addr
             );
         }
 #endif
 
         freeaddrinfo(res);
     }
 
     cfg.target_addr = target;
 
     esp_ping_callbacks_t cbs = {
         .on_ping_success = ping_on_success,
         .on_ping_timeout = ping_on_timeout,
         .on_ping_end     = ping_on_end
     };
 
     esp_ping_handle_t ping;
     esp_ping_new_session(&cfg, &cbs, &ping);
     esp_ping_start(ping);
 
     return 0;
 }
 