idf_component_register(
    SRCS
        "mod_cam.c"
        # "mod_trilat.c"  # Disabled for now - needs BT config
    INCLUDE_DIRS
        "."
    REQUIRES
        command
        esp_wifi
        nvs_flash
        esp_http_client
        espressif__esp32-camera
)
