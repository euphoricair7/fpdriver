import usb.core
import usb.util
import time

VID = 0x2808
PID = 0x93a9

dev = usb.core.find(idVendor=VID, idProduct=PID)
if not dev: raise ValueError("Device not found")
if dev.is_kernel_driver_active(0): dev.detach_kernel_driver(0)

dev.reset()
dev.set_configuration()

# Active Mode
print("Entering Active Mode (Reg 0x36 -> 1)...")
dev.ctrl_transfer(0x40, 0x36, 1, 0)
time.sleep(0.1)

TARGETS = [0x00, 0x63, 0x3C, 0xFC]

print("Reading 8 bytes from targets...")
for reg in TARGETS:
    try:
        ret = dev.ctrl_transfer(0xC0, reg, 0, 0, 8, timeout=100)
        print(f"Reg 0x{reg:02X}: {list(ret)}")
    except Exception as e:
        print(f"Reg 0x{reg:02X}: Failed - {e}")

print("\nTrying to toggle Reg 0x3C (Current Val 0x40?)...")
# Try writing 0, then 1, then 0x40?
vals = [0, 1, 0x40, 0x80]
for v in vals:
    print(f"Write 0x3C <- 0x{v:02X}")
    try:
        dev.ctrl_transfer(0x40, 0x3C, v, 0)
        st = dev.ctrl_transfer(0xC0, 0x02, 0, 0, 8)
        print(f"  Status: {list(st)}")
        
        # Poll Bulk
        try:
            data = dev.read(0x83, 1024, timeout=20)
            print(f"  [!!!] TRIGGERED DATA: {len(data)} bytes")
        except:
            pass
    except Exception as e:
        print(f"  Failed: {e}")

print("Done.")
