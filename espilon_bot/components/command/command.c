#include "command.h"
#include "utils.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "COMMAND";

static const command_t *registry[MAX_COMMANDS];
static size_t registry_count = 0;

/* =========================================================
 * Register command
 * ========================================================= */
void command_register(const command_t *cmd)
{
    if (!cmd || !cmd->name || !cmd->handler) {
        ESP_LOGE(TAG, "Invalid command registration");
        return;
    }

    if (registry_count >= MAX_COMMANDS) {
        ESP_LOGE(TAG, "Command registry full");
        return;
    }

    registry[registry_count++] = cmd;
    ESP_LOGI(TAG, "Registered command: %s", cmd->name);
}

/* =========================================================
 * Dispatch protobuf command
 * ========================================================= */
void command_process_pb(const c2_Command *cmd)
{
    if (!cmd) return;

    const char *name = cmd->command_name;
    int argc = cmd->argv_count;
    char **argv = (char **)cmd->argv;

    for (size_t i = 0; i < registry_count; i++) {
        const command_t *c = registry[i];

        if (strcmp(c->name, name) != 0)
            continue;

        /* Validate argc */
        if (argc < c->min_args || argc > c->max_args) {
            msg_error("cmd", "Invalid argument count",
                      cmd->request_id);
            return;
        }

        ESP_LOGI(TAG, "Execute: %s (argc=%d)", name, argc);

        if (c->async) {
            command_async_enqueue(c, cmd);
        } else {
            c->handler(argc, argv, cmd->request_id, c->ctx);
        }
        return;
    }

    msg_error("cmd", "Unknown command", cmd->request_id);
}
