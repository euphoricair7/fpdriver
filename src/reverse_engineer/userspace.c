#include <stdio.h>
#include <stdlib.h>
#include <libusb-1.0/libusb.h>

#define VENDOR_ID  0x2808   // Replace with actual VID
#define PRODUCT_ID 0x93a9   // Replace with actual PID
#define TIMEOUT    5000     // 5-second timeout

int main() {
    libusb_context *ctx = NULL;
    libusb_device_handle *handle = NULL;
    int r;

    // Initialize libusb
    if ((r = libusb_init(&ctx)) < 0) {
        fprintf(stderr, "Init error: %s\n", libusb_error_name(r));
        return 1;
    }

    // Open device
    handle = libusb_open_device_with_vid_pid(ctx, VENDOR_ID, PRODUCT_ID);
    if (!handle) {
        fprintf(stderr, "Device not found\n");
        libusb_exit(ctx);
        return 1;
    }

    // Claim interface
    if ((r = libusb_claim_interface(handle, 0)) < 0) {
        fprintf(stderr, "Claim error: %s\n", libusb_error_name(r));
        libusb_close(handle);
        libusb_exit(ctx);
        return 1;
    }

    // Send enrollment command
    unsigned char enroll_cmd[8] = {0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
    int transferred;
    r = libusb_bulk_transfer(handle, 0x01, enroll_cmd, sizeof(enroll_cmd), &transferred, TIMEOUT);
    if (r < 0) {
        fprintf(stderr, "Enroll command error: %s\n", libusb_error_name(r));
    }

    // Read response
    unsigned char response[8];
    r = libusb_bulk_transfer(handle, 0x81, response, sizeof(response), &transferred, TIMEOUT);
    if (r >= 0) {
        printf("ACK Received: ");
        for (int i = 0; i < transferred; i++) printf("%02X ", response[i]);
        printf("\n");
    }

    // Send capture command
    unsigned char capture_cmd[8] = {0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
    libusb_bulk_transfer(handle, 0x01, capture_cmd, sizeof(capture_cmd), &transferred, TIMEOUT);

    // Read image data
    unsigned char image_data[10240];  // Adjust based on expected size
    int total_bytes = 0;
    while (total_bytes < sizeof(image_data)) {
        r = libusb_bulk_transfer(handle, 0x81, image_data + total_bytes, 
                                sizeof(image_data) - total_bytes, &transferred, TIMEOUT);
        if (r < 0) break;
        total_bytes += transferred;
    }

    printf("Captured %d bytes of image data\n", total_bytes);

    // Save raw data
    FILE *fp = fopen("fingerprint.raw", "wb");
    fwrite(image_data, 1, total_bytes, fp);
    fclose(fp);

    // Cleanup
    libusb_release_interface(handle, 0);
    libusb_close(handle);
    libusb_exit(ctx);
    return 0;
}