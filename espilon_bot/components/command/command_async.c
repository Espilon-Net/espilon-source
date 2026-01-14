#include "command.h"
#include "utils.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include <string.h>

static const char *TAG = "CMD_ASYNC";

/* =========================================================
 * Async job structure
 * ========================================================= */
typedef struct {
    const command_t *cmd;
    int argc;
    char argv[MAX_ASYNC_ARGS][MAX_ASYNC_ARG_LEN];
    char *argv_ptrs[MAX_ASYNC_ARGS];
    char request_id[64];
} async_job_t;

static QueueHandle_t async_queue;

/* =========================================================
 * Worker task
 * ========================================================= */
static void async_worker(void *arg)
{
    async_job_t job;

    while (1) {
        if (xQueueReceive(async_queue, &job, portMAX_DELAY)) {
            ESP_LOGI(TAG, "Async exec: %s", job.cmd->name);

            job.cmd->handler(
                job.argc,
                job.argv_ptrs,
                job.request_id[0] ? job.request_id : NULL,
                job.cmd->ctx
            );
        }
    }
}

/* =========================================================
 * Init async system
 * ========================================================= */
void command_async_init(void)
{
    async_queue = xQueueCreate(8, sizeof(async_job_t));
    if (!async_queue) {
        ESP_LOGE(TAG, "Failed to create async queue");
        return;
    }

    xTaskCreate(
        async_worker,
        "cmd_async",
        4096,
        NULL,
        5,
        NULL
    );

    ESP_LOGI(TAG, "Async command system ready");
}

/* =========================================================
 * Enqueue async command
 * ========================================================= */
void command_async_enqueue(const command_t *cmd,
                           const c2_Command *pb_cmd)
{
    if (!cmd || !pb_cmd) return;

    async_job_t job = {0};

    job.cmd = cmd;
    job.argc = pb_cmd->argv_count;
    if (job.argc > MAX_ASYNC_ARGS)
        job.argc = MAX_ASYNC_ARGS;

    for (int i = 0; i < job.argc; i++) {
        strncpy(job.argv[i],
                pb_cmd->argv[i],
                MAX_ASYNC_ARG_LEN - 1);
        job.argv_ptrs[i] = job.argv[i];
    }

    if (pb_cmd->request_id[0]) {
        strncpy(job.request_id,
                pb_cmd->request_id,
                sizeof(job.request_id) - 1);
    }

    if (xQueueSend(async_queue, &job, 0) != pdTRUE) {
        ESP_LOGE(TAG, "Async queue full");
        msg_error("cmd", "Async queue full",
                  pb_cmd->request_id);
    }
}
