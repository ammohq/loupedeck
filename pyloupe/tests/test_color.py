import pytest
from pyloupe.color import parse_color


def test_parse_color_hex():
    assert parse_color("#FF00AA") == (255, 0, 170, 255)


def test_parse_color_short_hex():
    assert parse_color("#0F0") == (0, 255, 0, 255)


def test_parse_color_tuple():
    assert parse_color((1, 2, 3)) == (1, 2, 3, 255)


def test_parse_color_invalid():
    with pytest.raises(ValueError):
        parse_color(123)
