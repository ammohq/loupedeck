import struct
from unittest.mock import MagicMock

from pyloupe.device import LoupedeckDevice
from pyloupe.constants import COMMANDS


def test_update_firmware(tmp_path):
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"abcdefghij")

    device = LoupedeckDevice(auto_connect=False)
    device.send = MagicMock()

    device.update_firmware(str(fw), chunk_size=4)

    # Expect three chunks: 0-3, 4-7, 8-9
    assert device.send.call_count == 3

    first_call = device.send.call_args_list[0]
    assert first_call.args[0] == COMMANDS["FIRMWARE_UPDATE"]
    offset = struct.unpack("<I", first_call.args[1][:4])[0]
    assert offset == 0
    assert first_call.args[1][4:] == b"abcd"

