from pyloupe.parser import MagicByteLengthParser


def test_single_packet():
    parser = MagicByteLengthParser(0x82)
    packets = parser.feed(b"\x82\x03abc")
    assert packets == [b"abc"]


def test_split_packets():
    parser = MagicByteLengthParser(0x82)
    part1 = b"\x82\x02ab\x82\x03"
    part2 = b"cde"
    packets1 = parser.feed(part1)
    assert packets1 == [b"ab"]
    packets2 = parser.feed(part2)
    assert packets2 == [b"cde"]


def test_flush_buffer():
    parser = MagicByteLengthParser(0x82)
    parser.feed(b"\x82\x02a")
    # flush returns any buffered data unchanged
    assert parser.flush() == [b"\x82\x02a"]
