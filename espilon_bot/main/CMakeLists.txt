idf_component_register(SRCS "bot-lwip.c"
                    INCLUDE_DIRS "."
                    REQUIRES esp_wifi nvs_flash core mod_fakeAP mod_network mod_recon mod_system command)
