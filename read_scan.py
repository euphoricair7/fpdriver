import usb.core
import usb.util
import time

VID = 0x2808
PID = 0x93a9

dev = usb.core.find(idVendor=VID, idProduct=PID)
if not dev: raise ValueError("Device not found")

if dev.is_kernel_driver_active(0): dev.detach_kernel_driver(0)

# Reset
dev.reset()
dev.set_configuration()

# Active Mode
print("Entering Active Mode (Reg 0x36 -> 1)...")
try:
    dev.ctrl_transfer(0x40, 0x36, 1, 0)
    time.sleep(0.1)
except:
    print("Failed to set Active Mode")

print("Scanning READ 2 Bytes (0xC0 request) on all registers 0x00-0xFF...")

for reg in range(256):
    try:
        # Read 2 bytes
        ret = dev.ctrl_transfer(0xC0, reg, 0, 0, 2, timeout=50)
        val = list(ret)
        # Filter out 00 00 and FF FF
        if val != [0, 0] and val != [0xFF, 0xFF] and val != [0xC0, 0xC0]:
            print(f"Reg 0x{reg:02X} = {val}")
             
    except:
        pass # Ignore errors (stalls)

print("Scan Complete")
