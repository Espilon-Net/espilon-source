#include <stdint.h>
// dos.c
void start_dos(const char *t_ip, uint16_t t_port, int turn);

// arp.c
void arp_scan_task(void *pvParameters);

// ping.c
int do_ping_cmd(int argc, char **argv);

// proxy.c
void init_proxy(char *ip, int port);
