set(PRIV_REQUIRES_LIST 
    mbedtls
    lwip 
    mod_network 
    mod_fakeAP
    mod_recon
    esp_timer
    esp_driver_uart 
    driver
    command
)

idf_component_register(
    SRCS "crypto.c" "process.c" "WiFi.c" "gprs.c" "messages.c" "com.c"
        "nanoPB/c2.pb.c"
        "nanoPB/pb_common.c" 
        "nanoPB/pb_encode.c" 
        "nanoPB/pb_decode.c"
    INCLUDE_DIRS "." "nanoPB"

    PRIV_REQUIRES ${PRIV_REQUIRES_LIST}
)
