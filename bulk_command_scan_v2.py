
import usb.core
import usb.util
import time
import sys

# Device Info
VID = 0x2808
PID = 0x93a9

def main():
    print(f"Searching for device {hex(VID)}:{hex(PID)}...")
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print("Device not found")
        sys.exit(1)

    if dev.is_kernel_driver_active(0):
        try:
            dev.detach_kernel_driver(0)
            print("Kernel driver detached")
        except usb.core.USBError as e:
            print(f"Could not detach kernel driver: {str(e)}")

    try:
        dev.set_configuration()
        print("Configuration set")
    except usb.core.USBError as e:
        print(f"Could not set configuration: {str(e)}")

    # Endpoint addresses
    EP_OUT = 0x02
    EP_IN = 0x83
    
    # 0x140d0 Disassembly Analysis:
    # 0x20: 04 FB
    # 0x22: Command (0x1806 manipulated?)
    # 0x24: 00 01
    
    # Candidates from prior attempts
    payload1 = b'\x04\xfb\x06\x18\x00\x01\x00\x00' + b'\x00'*8
    payload2 = b'\xfb\x04\x18\x06\x01\x00\x00\x00' + b'\x00'*8
    payload3 = b'\xfc\x04\x06\x18\x00\x01\x00\x00' + b'\x00'*8

    # Calculated from 0x140d0 logic:
    # Arg: 0x1806 -> Result: 0x0698 (Little Endian: 98 06)
    # Header: 04 FB
    # Param: 00 01 (0x100)
    payload_calc = b'\x04\xfb\x98\x06\x00\x01\x00\x00' + b'\x00'*8
    
    # Try inverse 0x0698 -> 98 06 (Big Endian?) -> no, x86 is LE.
    
    tests = [
        ("04 FB Calculated (98 06)", payload_calc),
        ("04 FB Little Endian", payload1),
        ("FB 04 Big Endian", payload2),
        ("FC 04 Variant", payload3),
    ]

    for name, data in tests:
        print(f"\n--- Testing {name} ---")
        print(f"Sending: {data.hex()}")
        try:
            dev.write(EP_OUT, data, 1000)
            print("Write successful")
            
            try:
                resp = dev.read(EP_IN, 16, 1000)
                print(f"RESPONSE: {bytes(resp).hex()}")
                return # We found it!
            except usb.core.USBError as e:
                print(f"Read failed: {e}")
                
        except usb.core.USBError as e:
            print(f"Write failed: {e}")
        
        time.sleep(0.5)

if __name__ == "__main__":
    main()
