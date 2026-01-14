#pragma once

#include <stdbool.h>
#include <stddef.h>

#include "esp_err.h"     // 🔥 OBLIGATOIRE pour esp_err_t
#include "c2.pb.h"

/* ============================================================
 * Limits
 * ============================================================ */
#define MAX_COMMANDS      32
#define MAX_ASYNC_ARGS    8
#define MAX_ASYNC_ARG_LEN 64

/* ============================================================
 * Command handler prototype
 * ============================================================ */
typedef esp_err_t (*command_handler_t)(
    int argc,
    char **argv,
    const char *request_id,
    void *ctx
);

/* ============================================================
 * Command definition
 * ============================================================ */
typedef struct {
    const char *name;          /* command name */
    int min_args;
    int max_args;
    command_handler_t handler; /* handler */
    void *ctx;                 /* optional context */
    bool async;                /* async execution */
} command_t;

/* ============================================================
 * Registry
 * ============================================================ */
void command_register(const command_t *cmd);

/* ============================================================
 * Dispatcher (called by process.c)
 * ============================================================ */
void command_process_pb(const c2_Command *cmd);

/* ============================================================
 * Async support
 * ============================================================ */
void command_async_init(void);

void command_async_enqueue(
    const command_t *cmd,
    const c2_Command *pb_cmd
);
