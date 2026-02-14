import usb.core
import usb.util
import time

# Device Info
VID = 0x2808
PID = 0x93a9

# Find device
dev = usb.core.find(idVendor=VID, idProduct=PID)
if dev is None:
    raise ValueError('Device not found')

# Detach kernel driver
if dev.is_kernel_driver_active(0):
    dev.detach_kernel_driver(0)

# --- RESET WITH DELAY ---
print("Resetting...")
dev.reset()
time.sleep(0.5) # 500ms delay
dev.set_configuration()

# Helper for Control Transfers
def read_ctrl(req, val=0, idx=0, length=8):
    try:
        ret = dev.ctrl_transfer(0xC0, req, val, idx, length)
        # print(f"Read Req 0x{req:02X} -> {list(ret)}")
        return ret
    except:
        print(f"Read Req 0x{req:02X} FAILED")
        return None

# BASELINE
print("Getting Baseline Status...")
baseline = read_ctrl(0x02)
print(f"Initial Baseline: {list(baseline)}")

# FORCE STATE 04 (Active)
print("Forcing State 04 (Req 0x57)...")
try:
    dev.ctrl_transfer(0x40, 0x57, 1, 0)
    time.sleep(0.1)
    baseline = read_ctrl(0x02)
    print(f"Baseline (State 04): {list(baseline)}")
except:
    print("Failed to set State 04")

# TARGET REGISTERS
TARGETS = [0x01, 0x0C, 0x24] 

print("=== FULL wVALUE SCAN (0..255) ===")

for reg in TARGETS:
    print(f"\n--- Scanning Reg 0x{reg:02X} ---")
    for val in range(256):
        # Try Write
        try:
            dev.ctrl_transfer(0x40, reg, val, 0) 
        except:
            continue

        # Check Status Change
        try:
            st = dev.ctrl_transfer(0xC0, 0x02, 0, 0, 8)
            if list(st) != list(baseline):
                print(f"[!!!] Reg 0x{reg:02X} wVal=0x{val:04X} CHANGE STATUS: {list(st)}")
                
                # Check for Data
                try:
                    data = dev.read(0x83, 1024, timeout=20)
                    print(f"      AND TRIGGERED DATA: {len(data)} bytes")
                    exit(0) # FOUND IT!
                except:
                    pass
                
                # Restore baseline?
                # If it changed to something weird, maybe reset to 04?
                if list(st) != list(baseline):
                     dev.ctrl_transfer(0x40, 0x57, 1, 0) # Force back to 04
        except:
            pass
            
print("\nScan Complete")

