#pragma once
#include "lwip/ip4_addr.h"
#include <stdbool.h>

#define MAX_CLIENTS 10
#define CAPTIVE_PORTAL_IP  "192.168.4.1"
#define CAPTIVE_PORTAL_URL "http://192.168.4.1/"

/* DNS settings */
#define DNS_PORT 53
#define UPSTREAM_DNS "8.8.8.8"

/* ===== AUTH STATE ===== */
bool fakeap_is_authenticated(ip4_addr_t ip);
void fakeap_mark_authenticated(ip4_addr_t ip);

/* Internal use only - exported for mod_web_server.c */
extern ip4_addr_t authenticated_clients[MAX_CLIENTS];
extern int authenticated_count;
