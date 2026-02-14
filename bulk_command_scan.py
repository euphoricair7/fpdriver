import usb.core
import usb.util
import time
import struct

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

def send_bulk(data):
    try:
        # Pad to 16 bytes
        if len(data) < 16:
            data += b'\x00' * (16 - len(data))
        dev.write(0x02, data, timeout=100)
        return True
    except Exception as e:
        # print(f"  Write Failed: {e}")
        return False

def check_response():
    try:
        resp = dev.read(0x83, 64, timeout=50)
        return list(resp)
    except:
        return None

# PATTERNS TO TRY
# Helper to add checksums
def add_checksum(payload):
    # Method A: Sum (Last 2 bytes)
    s = sum(payload)
    p_sum = payload + struct.pack('>H', s & 0xFFFF)
    p_sum = p_sum.ljust(16, b'\x00')
    
    # Method B: XOR (Last byte)
    x = 0
    for b in payload: x ^= b
    p_xor = payload + bytes([x])
    p_xor = p_xor.ljust(16, b'\x00')
    
    return [p_sum, p_xor]

PATTERNS = []

# Base commands to try
CMDS = [
    [0x55, 0xAA, 0x01, 0x00], # 55 AA Sync + Cmd
    [0xAA, 0x55, 0x01, 0x00],
    [0xFC, 0x01, 0x00, 0x00], # FPC
    [0x01, 0x00, 0x00, 0x00], # Simple
]

RAW_PAYLOADS = []
for c in CMDS:
    base = bytes(c)
    RAW_PAYLOADS.append(base.ljust(16, b'\x00')) # Raw padded
    RAW_PAYLOADS.extend(add_checksum(base))      # With checksums

print("=== Bulk OUT Fuzzing with CHECKSUMS ===")
reset()

# Force Active Mode
try:
    dev.ctrl_transfer(0x40, 0x36, 1, 0)
    print("Entered Active Mode (0x36).")
except:
    print("Failed to set Active Mode.")

last_st = check_response() # endpoint 0x83 drain
last_ctrl = list(dev.ctrl_transfer(0xC0, 0x02, 0, 0, 8))
print(f"Initial Status: {last_ctrl}")

for p in RAW_PAYLOADS:
    hex_str = ''.join(f'{x:02X}' for x in p[:6]) + "..."
    # print(f"Sending: {hex_str}")
    
    if send_bulk(p):
        # 1. Check Bulk IN
        resp = check_response()
        if resp:
            print(f"[!!!] BULK RESPONSE to {hex_str}: {resp}")
            exit(0)
            
        # 2. Check Control Status Change?
        try:
            curr_ctrl = list(dev.ctrl_transfer(0xC0, 0x02, 0, 0, 8))
            if curr_ctrl != last_ctrl:
                print(f"[!] STATUS CHANGE to {hex_str}: {last_ctrl} -> {curr_ctrl}")
                last_ctrl = curr_ctrl
        except:
            pass
            
    time.sleep(0.01)

print("Done.")
