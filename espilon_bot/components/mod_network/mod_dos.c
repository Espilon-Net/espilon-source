/*
 * Eun0us - TCP Flood Simulation Module
 * Stream-based, non-destructive (simulation only)
 */

 #include <stdio.h>
 #include <string.h>
 #include <stdlib.h>
 
 #include "freertos/FreeRTOS.h"
 #include "freertos/task.h"
 #include "esp_log.h"
 
 #include "utils.h"
 
 #define TAG "MODULE_TCP_FLOOD"
 
 /* ============================================================
  * Configuration (SIMULATION)
  * ============================================================ */
 typedef struct {
     char ip[16];
     uint16_t port;
     int count;
 } flood_config_t;
 
 /* ============================================================
  * Simulated flood task (NO NETWORK)
  * ============================================================ */
 static void flood_sim_task(void *param)
 {
     flood_config_t *cfg = (flood_config_t *)param;
 
     msg_info(TAG, "Starting TCP flood simulation", NULL);
 
     for (int i = 0; i < cfg->count; i++) {
 
         char line[96];
         int len = snprintf(
             line,
             sizeof(line),
             "SIM SYN -> %s:%u (%d/%d)",
             cfg->ip,
             cfg->port,
             i + 1,
             cfg->count
         );
 
         if (len > 0) {
            msg_data(
                TAG, 
                line, 
                strlen(line), 
                false, 
                NULL);

         }
 
         vTaskDelay(pdMS_TO_TICKS(5));
     }
 
     /* End of stream */
     msg_data(TAG, NULL, 0, true, NULL);
 
     msg_info(TAG, "TCP flood simulation completed", NULL);
 
     free(cfg);
     vTaskDelete(NULL);
 }
 
 /* ============================================================
  * Public API (called by command)
  * ============================================================ */
 void start_dos(const char *t_ip, uint16_t t_port, int count)
 {
     if (!t_ip || count <= 0 || count > 10000) {
         msg_error(TAG, "invalid parameters (count 1-10000)", NULL);
         return;
     }
 
     flood_config_t *cfg = malloc(sizeof(flood_config_t));
     if (!cfg) {
         msg_error(TAG, "memory allocation failed", NULL);
         return;
     }
 
     strncpy(cfg->ip, t_ip, sizeof(cfg->ip) - 1);
     cfg->ip[sizeof(cfg->ip) - 1] = '\0';
     cfg->port = t_port;
     cfg->count = count;
 
     xTaskCreatePinnedToCore(
         flood_sim_task,
         "tcp_flood_sim",
         4096,
         cfg,
         5,
         NULL,
         1
     );
 }
 