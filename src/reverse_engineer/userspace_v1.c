#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <libusb-1.0/libusb.h>

/* 
 * Device Constants
 * Found via `lsusb` or Windows Device Manager
 */
#define VENDOR_ID  0x2808   // FocalTech
#define PRODUCT_ID 0x93a9   // FT9201
#define TIMEOUT    5000     // Timeout for USB transfers (ms)

/* 
 * USB Endpoints
 * Found via `lsusb -v`
 * EP 0x02: OUT (Host -> Device) for commands
 * EP 0x83: IN  (Device -> Host) for responses/images
 */
#define EP_OUT     0x02
#define EP_IN      0x83

// Placeholder Command - WE NEED TO FIND THE REAL MAGIC BYTES!
// Usually 8 or 16 bytes. 
unsigned char CMD_ENROLL[] = {0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}; // GUESS
unsigned char CMD_CAPTURE[] = {0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}; // GUESS

// BMP Header Structure (14 bytes file header + 40 bytes info header)
#pragma pack(push, 1) // Ensure no padding
struct BMPHeader {
    uint16_t bfType;      // "BM"
    uint32_t bfSize;      // File size
    uint16_t bfReserved1; // 0
    uint16_t bfReserved2; // 0
    uint32_t bfOffBits;   // Offset to image data
    
    // Info Header
    uint32_t biSize;      // Size of Info Header (40)
    int32_t  biWidth;     // Width
    int32_t  biHeight;    // Height (negative for top-down)
    uint16_t biPlanes;    // 1
    uint16_t biBitCount;  // 8 for grayscale
    uint32_t biCompression; // 0 (Uncompressed)
    uint32_t biSizeImage;   // Image size
    int32_t  biXPelsPerMeter;
    int32_t  biYPelsPerMeter;
    uint32_t biClrUsed;     // 256 for grayscale palette
    uint32_t biClrImportant;
};
#pragma pack(pop)

void save_bmp(const char *filename, unsigned char *data, int width, int height) {
    FILE *f = fopen(filename, "wb");
    if (!f) return;

    // Create Grayscale Palette
    unsigned char palette[1024];
    for(int i=0; i<256; i++) {
        palette[i*4+0] = i; // Blue
        palette[i*4+1] = i; // Green
        palette[i*4+2] = i; // Red
        palette[i*4+3] = 0; // Reserved
    }

    struct BMPHeader hdr = {0};
    hdr.bfType = 0x4D42; // "BM"
    hdr.bfOffBits = sizeof(struct BMPHeader) + sizeof(palette);
    hdr.bfSize = hdr.bfOffBits + (width * height);
    hdr.biSize = 40;
    hdr.biWidth = width;
    hdr.biHeight = -height; // Top-down
    hdr.biPlanes = 1;
    hdr.biBitCount = 8;     // 8-bit grayscale
    hdr.biSizeImage = width * height;
    hdr.biClrUsed = 256;

    fwrite(&hdr, sizeof(hdr), 1, f);
    fwrite(palette, sizeof(palette), 1, f);
    fwrite(data, 1, width * height, f);
    fclose(f);
    printf("Saved %s (%dx%d)\n", filename, width, height);
}

int main() {
    libusb_context *ctx = NULL;
    libusb_device_handle *handle = NULL;
    int r;
    int transferred;

    printf("Initializing libusb...\n");
    if ((r = libusb_init(&ctx)) < 0) {
        fprintf(stderr, "Init Error: %s\n", libusb_error_name(r));
        return 1;
    }
    // Set debug level to see detailed logs
    libusb_set_option(ctx, LIBUSB_OPTION_LOG_LEVEL, LIBUSB_LOG_LEVEL_INFO);

    printf("Opening device %04x:%04x...\n", VENDOR_ID, PRODUCT_ID);
    handle = libusb_open_device_with_vid_pid(ctx, VENDOR_ID, PRODUCT_ID);
    if (!handle) {
        fprintf(stderr, "Device not found. Check permissions (try sudo) or connection.\n");
        libusb_exit(ctx);
        return 1;
    }

    // Auto-detach kernel driver if one is active (rare for this device, but good practice)
    if (libusb_kernel_driver_active(handle, 0) == 1) {
        printf("Detaching kernel driver...\n");
        libusb_detach_kernel_driver(handle, 0);
    }

    printf("Claiming Interface 0...\n");
    if ((r = libusb_claim_interface(handle, 0)) < 0) {
        fprintf(stderr, "Claim Error: %s\n", libusb_error_name(r));
        goto cleanup;
    }

    // --- STEP 1: SEND ENROLL/INIT COMMAND ---
    // We need the REAL command from Wireshark here.
    printf("\n[Step 1] Sending Init/Enroll Command...\n");
    r = libusb_bulk_transfer(handle, EP_OUT, CMD_ENROLL, sizeof(CMD_ENROLL), &transferred, TIMEOUT);
    if (r < 0) {
        fprintf(stderr, "Write Error: %s\n", libusb_error_name(r));
    } else {
        printf("Sent %d bytes to EP 0x%02x\n", transferred, EP_OUT);
    }

    // --- STEP 2: READ RESPONSE/ACK ---
    unsigned char response[64];
    printf("\n[Step 2] Reading Response...\n");
    r = libusb_bulk_transfer(handle, EP_IN, response, sizeof(response), &transferred, TIMEOUT);
    if (r == 0) {
        printf("Received %d bytes: ", transferred);
        for (int i = 0; i < transferred; i++) printf("%02X ", response[i]);
        printf("\n");
    } else {
        fprintf(stderr, "Read Error: %s (Device might not reply if command was wrong)\n", libusb_error_name(r));
    }

    // --- STEP 3: CAPTURE IMAGE ---
    printf("\n[Step 3] Sending Capture Command...\n");
    libusb_bulk_transfer(handle, EP_OUT, CMD_CAPTURE, sizeof(CMD_CAPTURE), &transferred, TIMEOUT);

    // --- STEP 4: READ IMAGE DATA ---
    // Image size is unknown. Let's guess typical sizes:
    // 160x160 = 25600 bytes
    // 192x192 = 36864 bytes
    // Let's alloc enough buffer.
    #define MAX_IMAGE_SIZE (1024 * 1024) // 1MB
    unsigned char *image_buffer = malloc(MAX_IMAGE_SIZE);
    int total_bytes = 0;
    int errors = 0;

    printf("\n[Step 4] Reading Bulk Data (Press Ctrl+C to stop if stuck)...\n");
    
    // Loop to read multiple packets until we get enough data or timeout
    while (total_bytes < MAX_IMAGE_SIZE && errors < 5) {
        r = libusb_bulk_transfer(handle, EP_IN, image_buffer + total_bytes, 
                                4096, &transferred, 1000); // 1s timeout
        if (r == 0) {
            printf("Read chunk: %d bytes\n", transferred);
            total_bytes += transferred;
            if (transferred < 64) {
                 // Short packet usually indicates end of transfer
                 printf("Short packet received, assuming end of image.\n");
                 break; 
            }
        } else if (r == LIBUSB_ERROR_TIMEOUT) {
            printf("Timeout waiting for data. If we got 0 bytes total, the command was probably wrong.\n");
            errors++;
        } else {
            fprintf(stderr, "Read fail: %s\n", libusb_error_name(r));
            errors++;
        }
    }

    printf("\nCaptured Total: %d bytes\n", total_bytes);

    if (total_bytes > 0) {
        // Save RAW
        FILE *fp = fopen("fingerprint.raw", "wb");
        fwrite(image_buffer, 1, total_bytes, fp);
        fclose(fp);
        printf("Saved fingerprint.raw\n");

        // Try to save BMP (Guessing dimensions, e.g. 160x160?)
        // If we don't know dimensions, this will look scrambled.
        // Common sizes: 160x160, 192x192, 256x360
        // You can try adjusting these values.
        int width = 160; 
        int height = total_bytes / width; 
        save_bmp("fingerprint_preview.bmp", image_buffer, width, height);
    }

    free(image_buffer);

cleanup:
    if (handle) {
        libusb_release_interface(handle, 0);
        libusb_close(handle);
    }
    libusb_exit(ctx);
    return 0;
}