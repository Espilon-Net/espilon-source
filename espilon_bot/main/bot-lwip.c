#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "esp_log.h"
#include "nvs_flash.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "utils.h"
#include "command.h"
#include "cmd_system.h"

/* Module headers */
#ifdef CONFIG_MODULE_NETWORK
#include "cmd_network.h"
#endif

#ifdef CONFIG_MODULE_FAKEAP
#include "cmd_fakeAP.h"
#endif

#ifdef CONFIG_MODULE_RECON
#include "cmd_recon.h"
#endif

static const char *TAG = "MAIN";

static void init_nvs(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
        ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {

        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "Booting system");

    init_nvs();
    vTaskDelay(pdMS_TO_TICKS(1200));

    /* =====================================================
     * Command system
     * ===================================================== */

    command_async_init();          // Async worker (Core 1)
    mod_system_register_commands();

    /* Register enabled modules */
#ifdef CONFIG_MODULE_NETWORK
    mod_network_register_commands();
    ESP_LOGI(TAG, "Network module loaded");
#endif

#ifdef CONFIG_MODULE_FAKEAP
    mod_fakeap_register_commands();
    ESP_LOGI(TAG, "FakeAP module loaded");
#endif

#ifdef CONFIG_MODULE_RECON
    #ifdef CONFIG_RECON_MODE_CAMERA
    mod_camera_register_commands();
    ESP_LOGI(TAG, "Camera module loaded");
    #endif
    #ifdef CONFIG_RECON_MODE_BLE_TRILAT
    mod_ble_trilat_register_commands();
    ESP_LOGI(TAG, "BLE Trilateration module loaded");
    #endif
#endif

    /* =====================================================
     * Network backend
     * ===================================================== */
    if (!com_init()) {
        ESP_LOGE(TAG, "Network backend init failed");
        return;
    }

    ESP_LOGI(TAG, "System ready");
}
