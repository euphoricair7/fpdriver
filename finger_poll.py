import usb.core
import usb.util
import time

VID = 0x2808
PID = 0x93a9

dev = usb.core.find(idVendor=VID, idProduct=PID)
if not dev: raise ValueError("Device not found")

if dev.is_kernel_driver_active(0): dev.detach_kernel_driver(0)

print("Resetting...")
dev.reset()
time.sleep(0.5)
dev.set_configuration()

def send_ctrl(req, val):
    try:
        dev.ctrl_transfer(0x40, req, val, 0)
    except:
        print(f"Write {req:02X} Failed")

def read_ctrl(req):
    try:
        return list(dev.ctrl_transfer(0xC0, req, 0, 0, 8))
    except:
        return None

print("Putting device in Active State (0x57)...")
send_ctrl(0x57, 1) # Force State 04

print("Enabling (0x01 w/ Val 1)...")
send_ctrl(0x01, 1)

print("=== POLLING FINGER PRESENCE (0x63, 0x6A) ===")
print("Touch sensor repeatedly!")

last_63 = []
last_6A = []

while True:
    r63 = read_ctrl(0x63)
    r6A = read_ctrl(0x6A)
    
    if r63 != last_63:
        print(f"[CHANGE 0x63] {r63}")
        last_63 = r63
        
    if r6A != last_6A:
        print(f"[CHANGE 0x6A] {r6A}")
        last_6A = r6A
        
    # Also poll Bulk just in case
    try:
        data = dev.read(0x83, 64, timeout=10)
        print(f"[BULK DATA] {len(data)} bytes")
    except:
        pass
        
    time.sleep(0.05)
