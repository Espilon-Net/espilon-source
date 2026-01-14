#include "utils.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "COM";

bool com_init(void)
{
#ifdef CONFIG_NETWORK_WIFI

    ESP_LOGI(TAG, "Init WiFi backend");

    wifi_init();

    /* Task WiFi déjà complète (connect + handshake + RX) */
    xTaskCreatePinnedToCore(
        tcp_client_task,
        "tcp_client_task",
        8192,
        NULL,
        1,
        NULL,
        0
    );

    return true;

#elif defined(CONFIG_NETWORK_GPRS)

    ESP_LOGI(TAG, "Init GPRS backend");

    setup_uart();
    setup_modem();

    xTaskCreatePinnedToCore(
        gprs_client_task,
        "gprs_client_task",
        8192,
        NULL,
        1,
        NULL,
        0
    );

    return true;

#else
#error "No network backend selected"
#endif
}
