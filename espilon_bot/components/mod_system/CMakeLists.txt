idf_component_register(
    SRCS
        cmd_system.c
    INCLUDE_DIRS .
    REQUIRES core command esp_timer nvs_flash spi_flash
)
