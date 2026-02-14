import usb.core
import usb.util

VID = 0x2808
PID = 0x93a9

dev = usb.core.find(idVendor=VID, idProduct=PID)
if not dev:
    print("Device not found")
    exit(1)

print("Device Found!")
for cfg in dev:
    print(f"Configuration {cfg.bConfigurationValue}")
    for intf in cfg:
        print(f"  Interface {intf.bInterfaceNumber}, Alt {intf.bAlternateSetting}")
        for ep in intf:
            print(f"    Endpoint 0x{ep.bEndpointAddress:02X}")
            print(f"      Type: {usb.util.endpoint_type(ep.bmAttributes)}")
            print(f"      Max Packet Size: {ep.wMaxPacketSize}")
