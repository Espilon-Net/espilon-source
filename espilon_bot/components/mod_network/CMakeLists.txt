idf_component_register(SRCS "cmd_network.c" "mod_ping.c" "mod_proxy.c" "mod_arp.c" "mod_dos.c"
                    INCLUDE_DIRS .
                    REQUIRES lwip protocol_examples_common esp_wifi core command)
