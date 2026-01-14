idf_build_get_property(target IDF_TARGET)

if(${target} STREQUAL "linux")
    # Header only library for linux

    idf_component_register(INCLUDE_DIRS include
                           SRCS protocol_examples_utils.c)
    return()
endif()

set(srcs "addr_from_stdin.c"
         "protocol_examples_utils.c")



idf_component_register(SRCS "${srcs}"
                       INCLUDE_DIRS "include"
                       PRIV_REQUIRES esp_netif driver esp_wifi vfs  esp_eth)

