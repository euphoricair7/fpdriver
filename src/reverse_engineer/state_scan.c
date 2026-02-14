#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

#define VENDOR_ID  0x2808
#define PRODUCT_ID 0x93a9

void write_reg(libusb_device_handle *handle, uint8_t reg, uint16_t val) {
    int r = libusb_control_transfer(handle, 
        LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_RECIPIENT_DEVICE | LIBUSB_ENDPOINT_OUT, 
        reg, val, 0, NULL, 0, 1000);
    if (r < 0) printf("Write 0x%02X Val 0x%04X Failed: %s\n", reg, val, libusb_error_name(r));
    else printf("Write 0x%02X Val 0x%04X OK\n", reg, val);
}

void read_status(libusb_device_handle *handle) {
    unsigned char buf[8];
    int r = libusb_control_transfer(handle, 
        LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_RECIPIENT_DEVICE | LIBUSB_ENDPOINT_IN, 
        0x02, 0, 0, buf, 8, 100);
    if (r > 0) printf("Status 0x02: %02X %02X\n", buf[0], buf[1]);
}

int main() {
    libusb_context *ctx = NULL;
    libusb_device_handle *handle = NULL;
    
    libusb_init(&ctx);
    handle = libusb_open_device_with_vid_pid(ctx, VENDOR_ID, PRODUCT_ID);
    if (!handle) return 1;
    
    if (libusb_kernel_driver_active(handle, 0) == 1) libusb_detach_kernel_driver(handle, 0);
    libusb_claim_interface(handle, 0);

    printf("Resetting...\n");
    libusb_reset_device(handle);
    usleep(300000);
    libusb_set_configuration(handle, 1);
    
    printf("=== SMART SEQUENCE ===\n");
    
    // 1. Initial Status
    read_status(handle);
    
    // 2. Wake Up?
    write_reg(handle, 0x00, 0x01); // Possible ID/Wake
    usleep(10000);
    
    // 3. Enable? (Seen in scanner)
    write_reg(handle, 0x01, 0x01);
    usleep(10000);
    
    // 4. Another Enable? (0x24 appeared in scanner with 00 24... -> maybe writes allowed?)
    write_reg(handle, 0x24, 0x01); 
    usleep(10000);

    read_status(handle);

    // 5. Trigger Capture (Try 0x01 with 0x40 - Start?)
    write_reg(handle, 0x01, 0x40);
    
    // 6. Poll Bulk
    printf("Polling Bulk...\n");
    unsigned char buf[4096];
    int transferred;
    
    for (int i=0; i<500; i++) { // 5s
        int r = libusb_bulk_transfer(handle, 0x83, buf, sizeof(buf), &transferred, 10);
        if (r == 0) {
            printf("[DATA] %d bytes\n", transferred);
        }
        usleep(10000);
    }
    
    libusb_close(handle);
    libusb_exit(ctx);
    return 0;
}
