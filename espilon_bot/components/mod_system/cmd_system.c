/*
* cmd_system.c
* Refactored for new command system (flat commands)
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_chip_info.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "command.h"
#include "utils.h"

#define TAG "SYSTEM"

/* ============================================================
 * COMMAND: system_reboot
 * ============================================================ */
static int cmd_system_reboot(
    int argc,
    char **argv,
    const char *req,
    void *ctx
) {
    (void)argc;
    (void)argv;
    (void)ctx;

    msg_info(TAG, "Rebooting device", req);

    vTaskDelay(pdMS_TO_TICKS(250));
    esp_restart();
    return 0;
}

/* ============================================================
 * COMMAND: system_mem
 * ============================================================ */
static int cmd_system_mem(
    int argc,
    char **argv,
    const char *req,
    void *ctx
) {
    (void)argc;
    (void)argv;
    (void)ctx;

    uint32_t heap_free = esp_get_free_heap_size();
    uint32_t heap_min  = esp_get_minimum_free_heap_size();
    size_t internal_free = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);

    char buf[256];
    snprintf(buf, sizeof(buf),
        "heap_free=%" PRIu32 " heap_min=%" PRIu32 " internal_free=%u",
        heap_free,
        heap_min,
        (unsigned)internal_free
    );

    msg_info(TAG, buf, req);
    return 0;
}

/* ============================================================
 * COMMAND: system_uptime
 * ============================================================ */
static int cmd_system_uptime(
    int argc,
    char **argv,
    const char *req,
    void *ctx
) {
    (void)argc;
    (void)argv;
    (void)ctx;

    uint64_t sec = esp_timer_get_time() / 1000000ULL;

    char buf[128];
    snprintf(buf, sizeof(buf),
        "uptime=%llu days=%llu h=%02llu m=%02llu s=%02llu",
        (unsigned long long)sec,
        (unsigned long long)(sec / 86400),
        (unsigned long long)((sec / 3600) % 24),
        (unsigned long long)((sec / 60) % 60),
        (unsigned long long)(sec % 60)
    );

    msg_info(TAG, buf, req);
    return 0;
}

/* ============================================================
 * COMMAND REGISTRATION
 * ============================================================ */
static const command_t system_cmds[] = {
    { "system_reboot", 0, 0, cmd_system_reboot, NULL, false },
    { "system_mem",    0, 0, cmd_system_mem,    NULL, false },
    { "system_uptime", 0, 0, cmd_system_uptime, NULL, false }
};

void mod_system_register_commands(void)
{
    ESP_LOGI(TAG, "Registering system commands");

    for (size_t i = 0; i < sizeof(system_cmds)/sizeof(system_cmds[0]); i++) {
        command_register(&system_cmds[i]);
    }
}
