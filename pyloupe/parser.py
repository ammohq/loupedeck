class MagicByteLengthParser:
    """Parser that splits incoming data by a magic byte followed by a length byte."""

    def __init__(self, magic_byte: int):
        self.delimiter = magic_byte
        self.buffer = b""

    def feed(self, chunk: bytes):
        data = self.buffer + chunk
        packets = []
        while True:
            position = data.find(bytes([self.delimiter]))
            if position == -1:
                break
            if len(data) < position + 2:
                break
            next_length = data[position + 1]
            expected_end = position + next_length + 2
            if len(data) < expected_end:
                break
            packets.append(data[position + 2 : expected_end])
            data = data[expected_end:]
        self.buffer = data
        return packets

    def flush(self):
        data = self.buffer
        self.buffer = b""
        return [data] if data else []
