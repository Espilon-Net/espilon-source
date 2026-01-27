#include "command.h"
#include "utils.h"
#include "esp_log.h"

#include <string.h>
#include <stdlib.h>

static const char *TAG = "COMMAND";

static const command_t *registry[MAX_COMMANDS];
static size_t registry_count = 0;

/* Max longueur lue/copied par arg (sécurité si non \0) */
#ifndef COMMAND_MAX_ARG_LEN
#define COMMAND_MAX_ARG_LEN 128
#endif

/* Max args temporaires qu’on accepte ici (doit couvrir tes commandes) */
#ifndef COMMAND_MAX_ARGS
#define COMMAND_MAX_ARGS 16
#endif

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
 * Helpers: deep-copy argv into one arena + argv[] pointers
 * ========================================================= */
static bool deepcopy_argv(char *const *argv_in,
                          int argc,
                          char ***argv_out,
                          char **arena_out,
                          const char *req_id)
{
    *argv_out = NULL;
    *arena_out = NULL;

    if (argc < 0) {
        msg_error("cmd", "Invalid argc", req_id);
        return false;
    }

    if (argc == 0) {
        char **argv0 = (char **)calloc(1, sizeof(char *));
        if (!argv0) {
            msg_error("cmd", "OOM copying argv", req_id);
            return false;
        }
        *argv_out = argv0;
        *arena_out = NULL;
        return true;
    }

    size_t total = 0;
    for (int i = 0; i < argc; i++) {
        const char *s = (argv_in && argv_in[i]) ? argv_in[i] : "";
        size_t n = strnlen(s, COMMAND_MAX_ARG_LEN);
        total += (n + 1);
    }

    char *arena = (char *)malloc(total ? total : 1);
    char **argv_copy = (char **)malloc((size_t)argc * sizeof(char *));
    if (!arena || !argv_copy) {
        free(arena);
        free(argv_copy);
        msg_error("cmd", "OOM copying argv", req_id);
        return false;
    }

    size_t off = 0;
    for (int i = 0; i < argc; i++) {
        const char *s = (argv_in && argv_in[i]) ? argv_in[i] : "";
        size_t n = strnlen(s, COMMAND_MAX_ARG_LEN);

        argv_copy[i] = &arena[off];
        memcpy(&arena[off], s, n);
        arena[off + n] = '\0';
        off += (n + 1);
    }

    *argv_out = argv_copy;
    *arena_out = arena;
    return true;
}

/* =========================================================
 * Dispatch nanopb command
 * ========================================================= */
void command_process_pb(const c2_Command *cmd)
{
    if (!cmd) return;

    /* nanopb: tableaux fixes => jamais NULL */
    const char *name  = cmd->command_name;
    const char *reqid = cmd->request_id;
    const char *reqid_or_null = (reqid[0] ? reqid : NULL);

    int argc = cmd->argv_count;

    for (size_t i = 0; i < registry_count; i++) {
        const command_t *c = registry[i];

        if (strcmp(c->name, name) != 0)
            continue;

        if (argc < c->min_args || argc > c->max_args) {
            msg_error("cmd", "Invalid argument count", reqid_or_null);
            return;
        }

        ESP_LOGI(TAG, "Execute: %s (argc=%d)", name, argc);

        if (c->async) {
            /* Ton async copie déjà argv/request_id dans une queue => OK */
            command_async_enqueue(c, cmd);
            return;
        }

        /* ================================
         * SYNC PATH (FIX):
         * Ne PAS caster cmd->argv en char**
         * On construit argv_ptrs[] depuis cmd->argv[i]
         * ================================ */
        if (argc > COMMAND_MAX_ARGS) {
            msg_error("cmd", "Too many args", reqid_or_null);
            return;
        }

        char *argv_ptrs[COMMAND_MAX_ARGS] = {0};
        for (int a = 0; a < argc; a++) {
            /* Fonctionne que cmd->argv soit char*[N] ou char[N][M] */
            argv_ptrs[a] = (char *)cmd->argv[a];
        }

        /* Deep-copy pour rendre sync aussi safe que async */
        char **argv_copy = NULL;
        char *arena = NULL;

        if (!deepcopy_argv(argv_ptrs, argc, &argv_copy, &arena, reqid_or_null))
            return;

        c->handler(argc, argv_copy, reqid_or_null, c->ctx);

        free(argv_copy);
        free(arena);
        return;
    }

    msg_error("cmd", "Unknown command", reqid_or_null);
}
