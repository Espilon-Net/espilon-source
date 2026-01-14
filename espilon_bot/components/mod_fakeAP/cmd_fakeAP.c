/*
* cmd_fakeAP.c
* Refactored for new command system
*/
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>

#include "esp_log.h"

#include "command.h"
#include "fakeAP_utils.h"
#include "utils.h"

#define TAG "CMD_FAKEAP"

/* ============================================================
 * State
 * ============================================================ */
static bool fakeap_running = false;
static bool portal_running = false;
static bool sniffer_running = false;

/* ============================================================
 * COMMAND: fakeap_start <ssid> [open|wpa2] [password]
 * ============================================================ */
static int cmd_fakeap_start(
    int argc,
    char **argv,
    const char *req,
    void *ctx
) {
    (void)ctx;

    if (argc < 1) {
        msg_error(TAG,
            "usage: fakeap_start <ssid> [open|wpa2] [password]",
            req);
        return -1;
    }

    if (fakeap_running) {
        msg_error(TAG, "FakeAP already running", req);
        return -1;
    }

    const char *ssid = argv[0];
    bool open = true;
    const char *password = NULL;

    if (argc >= 2) {
        if (!strcmp(argv[1], "open")) {
            open = true;
        } else if (!strcmp(argv[1], "wpa2")) {
            open = false;
            if (argc < 3) {
                msg_error(TAG, "WPA2 password required", req);
                return -1;
            }
            password = argv[2];
        } else {
            msg_error(TAG, "Unknown security mode", req);
            return -1;
        }
    }

    start_access_point(ssid, password, open);
    fakeap_running = true;

    msg_info(TAG, "FakeAP started", req);
    return 0;
}

/* ============================================================
 * COMMAND: fakeap_stop
 * ============================================================ */
static int cmd_fakeap_stop(
    int argc,
    char **argv,
    const char *req,
    void *ctx
) {
    (void)argc;
    (void)argv;
    (void)ctx;

    if (!fakeap_running) {
        msg_error(TAG, "FakeAP not running", req);
        return -1;
    }

    if (portal_running) {
        stop_captive_portal();
        portal_running = false;
    }

    if (sniffer_running) {
        stop_sniffer();
        sniffer_running = false;
    }

    stop_access_point();
    fakeap_running = false;

    msg_info(TAG, "FakeAP stopped", req);
    return 0;
}

/* ============================================================
 * COMMAND: fakeap_status
 * ============================================================ */
static int cmd_fakeap_status(
    int argc,
    char **argv,
    const char *req,
    void *ctx
) {
    (void)argc;
    (void)argv;
    (void)ctx;

    char buf[256];
    snprintf(buf, sizeof(buf),
        "FakeAP status:\n"
        " AP: %s\n"
        " Portal: %s\n"
        " Sniffer: %s\n"
        " Authenticated clients: %d",
        fakeap_running ? "ON" : "OFF",
        portal_running ? "ON" : "OFF",
        sniffer_running ? "ON" : "OFF",
        authenticated_count
    );

    msg_info(TAG, buf, req);
    return 0;
}

/* ============================================================
 * COMMAND: fakeap_clients
 * ============================================================ */
static int cmd_fakeap_clients(
    int argc,
    char **argv,
    const char *req,
    void *ctx
) {
    (void)argc;
    (void)argv;
    (void)ctx;

    if (!fakeap_running) {
        msg_error(TAG, "FakeAP not running", req);
        return -1;
    }

    list_connected_clients();
    return 0;
}

/* ============================================================
 * COMMAND: fakeap_portal_start
 * ============================================================ */
static int cmd_fakeap_portal_start(
    int argc,
    char **argv,
    const char *req,
    void *ctx
) {
    (void)argc;
    (void)argv;
    (void)ctx;

    if (!fakeap_running) {
        msg_error(TAG, "Start FakeAP first", req);
        return -1;
    }

    if (portal_running) {
        msg_error(TAG, "Captive portal already running", req);
        return -1;
    }

    start_captive_portal();
    portal_running = true;

    msg_info(TAG, "Captive portal enabled", req);
    return 0;
}

/* ============================================================
 * COMMAND: fakeap_portal_stop
 * ============================================================ */
static int cmd_fakeap_portal_stop(
    int argc,
    char **argv,
    const char *req,
    void *ctx
) {
    (void)argc;
    (void)argv;
    (void)ctx;

    if (!portal_running) {
        msg_error(TAG, "Captive portal not running", req);
        return -1;
    }

    stop_captive_portal();
    portal_running = false;

    msg_info(TAG, "Captive portal stopped", req);
    return 0;
}

/* ============================================================
 * COMMAND: fakeap_sniffer_on
 * ============================================================ */
static int cmd_fakeap_sniffer_on(
    int argc,
    char **argv,
    const char *req,
    void *ctx
) {
    (void)argc;
    (void)argv;
    (void)ctx;

    if (sniffer_running) {
        msg_error(TAG, "Sniffer already running", req);
        return -1;
    }

    start_sniffer();
    sniffer_running = true;

    msg_info(TAG, "Sniffer enabled", req);
    return 0;
}

/* ============================================================
 * COMMAND: fakeap_sniffer_off
 * ============================================================ */
static int cmd_fakeap_sniffer_off(
    int argc,
    char **argv,
    const char *req,
    void *ctx
) {
    (void)argc;
    (void)argv;
    (void)ctx;

    if (!sniffer_running) {
        msg_error(TAG, "Sniffer not running", req);
        return -1;
    }

    stop_sniffer();
    sniffer_running = false;

    msg_info(TAG, "Sniffer disabled", req);
    return 0;
}

/* ============================================================
 * REGISTER COMMANDS
 * ============================================================ */
static const command_t fakeap_cmds[] = {
    { "fakeap_start",        1, 3, cmd_fakeap_start,        NULL, false },
    { "fakeap_stop",         0, 0, cmd_fakeap_stop,         NULL, false },
    { "fakeap_status",       0, 0, cmd_fakeap_status,       NULL, false },
    { "fakeap_clients",      0, 0, cmd_fakeap_clients,      NULL, false },
    { "fakeap_portal_start", 0, 0, cmd_fakeap_portal_start, NULL, false },
    { "fakeap_portal_stop",  0, 0, cmd_fakeap_portal_stop,  NULL, false },
    { "fakeap_sniffer_on",   0, 0, cmd_fakeap_sniffer_on,   NULL, false },
    { "fakeap_sniffer_off",  0, 0, cmd_fakeap_sniffer_off,  NULL, false }
};
 
void mod_fakeap_register_commands(void)
{
    for (size_t i = 0; i < sizeof(fakeap_cmds)/sizeof(fakeap_cmds[0]); i++) {
        command_register(&fakeap_cmds[i]);
    }
}
 