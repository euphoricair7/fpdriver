import usb.core
import usb.util
import time

VID = 0x2808
PID = 0x93a9

dev = usb.core.find(idVendor=VID, idProduct=PID)
if not dev: raise ValueError("Device not found")
if dev.is_kernel_driver_active(0): dev.detach_kernel_driver(0)

def reset():
    print("Resetting...")
    dev.reset()
    time.sleep(0.5)
    dev.set_configuration()

def w(reg, val):
    try:
        dev.ctrl_transfer(0x40, reg, val, 0)
        # print(f"  -> Write 0x{reg:02X} = 0x{val:02X}")
        return True
    except:
        print(f"  -> Write 0x{reg:02X} FAILED")
        return False

def r_status():
    try:
        ret = dev.ctrl_transfer(0xC0, 0x02, 0, 0, 8)
        return list(ret)
    except:
        return None

def poll_bulk():
    try:
        data = dev.read(0x83, 16384, timeout=50) # Fast poll
        return len(data)
    except:
        return 0

# TEST SEQUENCES
# Tuples of (Reg, Val)
# TEST SEQUENCES
# Tuples of (Reg, Val)
# NOTE: We prepend (0x36, 1) to everything because we know it wakes the device.
SEQUENCES = [
    # User Suggestion (modified with wake)
    [(0x36, 1), (0x01, 1), (0x02, 1), (0x10, 1)],
    
    # Init-like chains
    [(0x36, 1), (0x01, 1), (0x0C, 1)], # logic: wake -> enable -> mode?
    [(0x36, 1), (0xFC, 0), (0x01, 1)], # FPC style?
    
    # "Unlock" + "Enable"
    [(0x36, 1), (0x00, 1), (0x01, 1)],
    
    # Try 0x10 (common enable)
    [(0x36, 1), (0x10, 1)],
    
    # Try writing 0 to 0x3C then 1
    [(0x36, 1), (0x3C, 0), (0x3C, 1)],
    
    # Try interacting with 0x00 (ID/Lock?)
    [(0x36, 1), (0x00, 0), (0x00, 1)],
]

for i, seq in enumerate(SEQUENCES):
    print(f"\n=== SEQUENCE {i}: {seq} ===")
    reset()
    last_st = r_status()
    print(f"Start Status: {last_st}")
    
    for (reg, val) in seq:
        print(f"Step: Reg 0x{reg:02X} <- 0x{val:02X}")
        w(reg, val)
        time.sleep(0.05)
        
        curr_st = r_status()
        if curr_st != last_st:
            print(f"  [!] STATUS CHANGED: {last_st} -> {curr_st}")
            last_st = curr_st
            
        # Poll for data constantly
        bytes_in = poll_bulk()
        if bytes_in > 0:
            print(f"  [!!!] DATA RECEIVED: {bytes_in} bytes")
            exit(0)

print("\nDone.")
