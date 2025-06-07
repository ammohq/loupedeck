from . import device


def discover(**kwargs):
    devices = device.LoupedeckDevice.list()
    if not devices:
        raise RuntimeError("No devices found")
    dev_info = devices[0]
    product_id = dev_info.get("productId")
    device_class = None
    for obj in device.__dict__.values():
        if hasattr(obj, "productId") and getattr(obj, "productId") == product_id:
            device_class = obj
            break
    if not device_class:
        raise RuntimeError(f"Device with product ID {product_id} not yet supported")
    args = {
        k: v for k, v in dev_info.items() if k not in ("productId", "connectionType")
    }
    args.update(kwargs)
    return device_class(**args)
