idf_component_register(SRCS "mod_web_server.c" "mod_fakeAP.c" "mod_netsniff.c"
                    INCLUDE_DIRS .
                    REQUIRES esp_http_server
                    PRIV_REQUIRES esp_netif lwip esp_wifi esp_event nvs_flash core)