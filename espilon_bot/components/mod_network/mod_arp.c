/*
 * Eun0us - ARP Scan Module
 * Stream-based local network discovery
 */

 #include "freertos/FreeRTOS.h"
 #include "freertos/task.h"
 
 #include "esp_log.h"
 #include "esp_netif.h"
 #include "esp_netif_net_stack.h"
 
 #include "lwip/ip4_addr.h"
 #include "lwip/etharp.h"
 
 #include <stdio.h>
 #include <string.h>
 
 #include "utils.h"
 
 #define TAG "ARP_SCAN"
 #define ARP_TIMEOUT_MS 5000
 #define ARP_BATCH_SIZE 5
 
 /* ============================================================
  * Helpers
  * ============================================================ */
 
 /* Convert little/big endian safely */
 static uint32_t swap_u32(uint32_t v)
 {
     return ((v & 0xFF000000U) >> 24) |
            ((v & 0x00FF0000U) >> 8)  |
            ((v & 0x0000FF00U) << 8)  |
            ((v & 0x000000FFU) << 24);
 }
 
 static void next_ip(esp_ip4_addr_t *ip)
 {
     esp_ip4_addr_t tmp;
     tmp.addr = swap_u32(ip->addr);
     tmp.addr++;
     ip->addr = swap_u32(tmp.addr);
 }
 
 /* ============================================================
  * ARP scan task
  * ============================================================ */
 
 void arp_scan_task(void *pvParameters)
 {
     (void)pvParameters;
 
     msg_info(TAG, "ARP scan started", NULL);
 
     esp_netif_t *netif_handle =
         esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
     if (!netif_handle) {
         msg_error(TAG, "wifi netif not found", NULL);
         vTaskDelete(NULL);
         return;
     }
 
     struct netif *lwip_netif =
         esp_netif_get_netif_impl(netif_handle);
     if (!lwip_netif) {
         msg_error(TAG, "lwIP netif not found", NULL);
         vTaskDelete(NULL);
         return;
     }
 
     esp_netif_ip_info_t ip_info;
     esp_netif_get_ip_info(netif_handle, &ip_info);
 
     /* Compute network range */
     esp_ip4_addr_t start_ip;
     start_ip.addr = ip_info.ip.addr & ip_info.netmask.addr;
 
     esp_ip4_addr_t end_ip;
     end_ip.addr = start_ip.addr | ~ip_info.netmask.addr;
 
     esp_ip4_addr_t cur_ip = start_ip;
 
     char ip_str[IP4ADDR_STRLEN_MAX];
     char json[128];
 
     while (cur_ip.addr != end_ip.addr) {
 
         esp_ip4_addr_t batch[ARP_BATCH_SIZE];
         int batch_count = 0;
 
         /* Send ARP requests */
         for (int i = 0; i < ARP_BATCH_SIZE; i++) {
             next_ip(&cur_ip);
             if (cur_ip.addr == end_ip.addr)
                 break;
 
             etharp_request(
                 lwip_netif,
                 (const ip4_addr_t *)&cur_ip
             );
 
             batch[batch_count++] = cur_ip;
         }
 
         /* Wait for replies */
         vTaskDelay(pdMS_TO_TICKS(ARP_TIMEOUT_MS));
 
         /* Collect results */
         for (int i = 0; i < batch_count; i++) {
             struct eth_addr *mac = NULL;
             const ip4_addr_t *ip_ret = NULL;
 
             if (etharp_find_addr(
                     lwip_netif,
                     (const ip4_addr_t *)&batch[i],
                     &mac,
                     &ip_ret
                 ) == ERR_OK && mac) {
 
                 esp_ip4addr_ntoa(
                     &batch[i],
                     ip_str,
                     sizeof(ip_str)
                 );
 
                 int len = snprintf(
                     json,
                     sizeof(json),
                     "{"
                     "\"ip\":\"%s\","
                     "\"mac\":\"%02X:%02X:%02X:%02X:%02X:%02X\""
                     "}",
                     ip_str,
                     mac->addr[0], mac->addr[1], mac->addr[2],
                     mac->addr[3], mac->addr[4], mac->addr[5]
                 );
 
                 if (len > 0) {
                     /* 1 host = 1 streamed event */
                     msg_data(
                         TAG,
                         json,
                         len,
                         false,  /* eof */
                         NULL
                     );
                 }
             }
         }
     }
 
     msg_info(TAG, "ARP scan completed", NULL);
 
     /* End of stream */
     msg_data(TAG, NULL, 0, true, NULL);
 
     vTaskDelete(NULL);
 }
 