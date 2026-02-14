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

def write_reg(reg, val):
    dev.ctrl_transfer(0x40, reg, val, 0)

def read_status():
    return list(dev.ctrl_transfer(0xC0, 0x02, 0, 0, 8))

def poll_bulk():
    try:
        data = dev.read(0x83, 16384, timeout=100)
        return len(data)
    except:
        return 0

reset()
print(f"Initial Status: {read_status()}")

# 1. Switch to Active Mode
print("Sending 0x36 (Active Mode)...")
write_reg(0x36, 1)
st = read_status()
print(f"Status after 0x36: {st}")

if st[0] != 0x00:
    print("Failed to enter Active Mode?")
    
# 2. Try to trigger capture
# Try common trigger registers: 0x01, 0x0C, 0x24 with common values
TRIGGERS = [
    (0x01, 0x01), (0x01, 0x40), 
    (0x0C, 0x01), 
    (0x24, 0x01)
]

print("Trying triggers in Active Mode...")
for reg, val in TRIGGERS:
    print(f"Write Reg 0x{reg:02X} Val 0x{val:02X}")
    try:
        write_reg(reg, val)
        bytes_read = poll_bulk()
        if bytes_read > 0:
            print(f"[!!!] SUCCESS! Triggered {bytes_read} bytes")
            break
        
        # Check if status changed
        st_new = read_status()
        if st_new != st:
            print(f"  Status Changed to: {st_new}")
            st = st_new
            
    except Exception as e:
        print(f"  Error: {e}")

# 3. If no trigger, scan all in Active Mode
print("\nScanning all registers (0x00-0xFF) in Active Mode with value 1...")
for reg in range(256):
    if reg == 0x36 or reg == 0x57: continue # Skip state changers
    try:
        write_reg(reg, 1)
        # Check bulk
        res = poll_bulk()
        if res > 0: 
            print(f"[!!!] HIT! Reg 0x{reg:02X} triggered {res} bytes")
            break
        # Restore active mode if kicked out
        curr_st = read_status()
        if curr_st[0] != 0x00:
            print(f"  Reg 0x{reg:02X} kicked out of Active Mode to {curr_st}. Restoring...")
            write_reg(0x36, 1)
            time.sleep(0.01)
    except:
        pass

print("Done.")
