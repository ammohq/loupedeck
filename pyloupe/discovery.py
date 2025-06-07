from typing import Any, Dict, Type
from . import device


def discover(**kwargs: Any) -> device.LoupedeckDevice:
    """Discover and connect to a Loupedeck device.

    This function automatically discovers available Loupedeck devices,
    determines the appropriate device class based on the product ID,
    and creates an instance of that class.

    Args:
        **kwargs: Additional keyword arguments to pass to the device constructor

    Returns:
        An instance of LoupedeckDevice or one of its subclasses

    Raises:
        RuntimeError: If no devices are found or if the discovered device is not supported
    """
    devices = device.LoupedeckDevice.list()
    if not devices:
        raise RuntimeError("No devices found")
    dev_info = devices[0]
    product_id = dev_info.get("productId")
    device_class: Type[device.LoupedeckDevice] = None
    for obj in device.__dict__.values():
        if hasattr(obj, "productId") and getattr(obj, "productId") == product_id:
            device_class = obj
            break
    if not device_class:
        raise RuntimeError(f"Device with product ID {product_id} not yet supported")
    args: Dict[str, Any] = {
        k: v for k, v in dev_info.items() if k not in ("productId", "connectionType")
    }
    args.update(kwargs)
    return device_class(**args)
