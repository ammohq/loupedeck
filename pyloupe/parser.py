from typing import List


class MagicByteLengthParser:
    """Parser that splits incoming data by a magic byte followed by a length byte.

    This parser is used to extract packets from a stream of bytes where each packet
    starts with a magic byte, followed by a length byte, and then the packet data.
    """

    def __init__(self, magic_byte: int) -> None:
        """Initialize the parser with a magic byte.

        Args:
            magic_byte: The byte value that marks the start of a packet
        """
        self.delimiter = magic_byte
        self.buffer = b""

    def feed(self, chunk: bytes) -> List[bytes]:
        """Feed data into the parser and extract complete packets.

        Args:
            chunk: New data to be parsed

        Returns:
            A list of complete packets extracted from the data
        """
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

    def flush(self) -> List[bytes]:
        """Flush the buffer and return any remaining data as a packet.

        Returns:
            A list containing the remaining data as a packet, or an empty list if no data remains
        """
        data = self.buffer
        self.buffer = b""
        return [data] if data else []
