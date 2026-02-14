#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <libusb-1.0/libusb.h>

#define VENDOR_ID  0x2808
#define PRODUCT_ID 0x93a9

int main() {
    libusb_context *ctx = NULL;
    libusb_device_handle *handle = NULL;
    int r;

    if (libusb_init(&ctx) < 0) return 1;
    // libusb_set_option(ctx, LIBUSB_OPTION_LOG_LEVEL, LIBUSB_LOG_LEVEL_INFO);

    handle = libusb_open_device_with_vid_pid(ctx, VENDOR_ID, PRODUCT_ID);
    if (!handle) { fprintf(stderr, "Device not found\n"); return 1; }

    if (libusb_kernel_driver_active(handle, 0) == 1) libusb_detach_kernel_driver(handle, 0);
    libusb_claim_interface(handle, 0);

    printf("Resetting...\n");
    libusb_reset_device(handle);
    libusb_set_configuration(handle, 1);
    
    // Initial Status Check
    unsigned char stbox[8];
    libusb_control_transfer(handle, 0xC0, 0x02, 0, 0, stbox, 8, 100);
    printf("Initial Status 0x02: %02X %02X\n", stbox[0], stbox[1]);

    printf("\n=== BRUTE FORCE INIT (0x00 - 0x60) ===\n");
    
    for (int req = 0; req <= 0x60; req++) {
        // Try to Write '1' to this register
        // printf("Trying Reg 0x%02X Val 1... ", req);
        r = libusb_control_transfer(handle, 
            LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_RECIPIENT_DEVICE | LIBUSB_ENDPOINT_OUT, 
            req, 1, 0, NULL, 0, 100); // 100ms timeout
        
        if (r >= 0) {
            // ACKed!
            // Check if Status 0x02 Changed?
            unsigned char buf[8];
            libusb_control_transfer(handle, 0xC0, 0x02, 0, 0, buf, 8, 50);
            
            // Use 0x02 as indicator. If it changes from 00 to anything else.
            if (buf[0] != stbox[0] || buf[1] != stbox[1]) {
                 printf("\n[!!!] HIT! Reg 0x%02X caused Status Change: %02X%02X -> %02X%02X\n",
                     req, stbox[0], stbox[1], buf[0], buf[1]);
                 // Update baseline
                 stbox[0] = buf[0]; stbox[1] = buf[1];
            }

            // Check Bulk IN
            unsigned char bulk[64];
            int transferred;
            r = libusb_bulk_transfer(handle, 0x83, bulk, 64, &transferred, 20); // Fast check
            if (r == 0) {
                printf("\n[!!!] HIT! Reg 0x%02X triggered BULK DATA %d bytes!\n", req, transferred);
                for(int i=0; i<transferred; i++) printf("%02X ", bulk[i]);
                printf("\n");
                break; // Stop on first data
            }
        }
    }
    
    printf("\nScan Complete.\n");

    libusb_close(handle);
    libusb_exit(ctx);
    return 0;
}