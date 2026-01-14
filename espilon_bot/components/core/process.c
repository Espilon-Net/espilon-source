#include <string.h>

#include "c2.pb.h"
#include "command.h"
#include "utils.h"
#include "esp_log.h"

static const char *TAG = "PROCESS";

/* =========================================================
 * UNIQUE ENTRY POINT — C2 → ESP
 * ========================================================= */
void process_command(const c2_Command *cmd)
{
    if (!cmd) {
        ESP_LOGE(TAG, "NULL command");
        return;
    }

    /* -----------------------------------------------------
     * Device ID check
     * ----------------------------------------------------- */
    //if (!device_id_matches(CONFIG_DEVICE_ID, cmd->device_id)) {
    //    ESP_LOGW(TAG,
    //             "Command not for this device (target=%s)",
    //             cmd->device_id);
    //    return;
    //}

    /* -----------------------------------------------------
     * Basic validation
     * ----------------------------------------------------- */
    if (cmd->command_name[0] == '\0') {
        msg_error(TAG, "Empty command name", cmd->request_id);
        return;
    }

    ESP_LOGI(TAG,
             "CMD received: %s (argc=%d)",
             cmd->command_name,
             cmd->argv_count);

    /* -----------------------------------------------------
     * Dispatch to command engine
     * ----------------------------------------------------- */
    command_process_pb(cmd);
}
