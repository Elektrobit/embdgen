# SPDX-License-Identifier: GPL-3.0-only

from typing import Optional
import pytest
from embdgen.core.utils.SizeType import SizeType, BYTES_PER_SECTOR


COMPARE_TABLE_LT = [
#   left   right lt
    (None, None, False),
    (0,    None, True),
    (None, 0,    False),
    (0,    0,    False),
    (0,    1,    True),
    (1,    0,    False)
]

COMPARE_TABLE_LE = [
    (left, right, lt or left == right)
    for left, right, lt in COMPARE_TABLE_LT
]

COMPARE_TABLE_GT = [
    (left, right, not le)
    for left, right, le in COMPARE_TABLE_LE
]

COMPARE_TABLE_GE = [
    (left, right, gt or left == right)
    for left, right, gt in COMPARE_TABLE_GT
]

COMPARE_TABLE_EQ = [
    (left, right, left == right)
    for left, right, _ in COMPARE_TABLE_LT
]

COMPARE_TABLE_NE = [
    (left, right, left != right)
    for left, right, _ in COMPARE_TABLE_LT
]

class TestSizeType:
    @pytest.mark.parametrize(
        "data, bytes_val",
        [
            ("0",          0),
            ("0 B",        0),
            ("0 S",        0),
            ("1 B",        1),
            ("5 kB",       5 * 1024),
            ("12 MB",      12 *1024 * 1024),
            ("18 GB",      18 * 1024 * 1024 * 1024),
            ("0x100 MB",   0x100 * 1024 * 1024),
            ("8 S",        8 * BYTES_PER_SECTOR),
            ("0x123 S",    0x123 * BYTES_PER_SECTOR),
            ("123 456 kB", 123456 * 1024),
            ("0xf B",      0xf),
            ("0xF B",      0xF)
        ]
    )
    def test_parse(self, data: str, bytes_val: int):
        assert SizeType.parse(data).bytes == bytes_val

    @pytest.mark.parametrize(
        "data",
        [
            "",
            "12",
            "12 MGB"
            "abc",
            "aa B",
            "0xfg B",
            "-5 S",
            "-5 B"
        ]
    )
    def test_parse_invalid(self, data: str):
        with pytest.raises(Exception):
            SizeType.parse(data)

    @pytest.mark.parametrize(
        "bytes_val, expected",
        [
            (0,                        True),
            (BYTES_PER_SECTOR,         True),
            (5 * BYTES_PER_SECTOR,     True),
            (1,                        False),
            (BYTES_PER_SECTOR - 1,     False),
            (5 * BYTES_PER_SECTOR + 1, False),
            (5 * BYTES_PER_SECTOR - 1, False)
        ]
    )
    def test_is_sector_aligned(self, bytes_val: str, expected: bool):
        if expected:
            assert SizeType(bytes_val).is_sector_aligned
        else:
            assert not SizeType(bytes_val).is_sector_aligned

    @pytest.mark.parametrize(
        "bytes_val, sectors",
        [
            (0,                       0),
            (BYTES_PER_SECTOR,        1),
            (5 * BYTES_PER_SECTOR,    5)
        ]
    )
    def test_sectors(self, bytes_val: str, sectors: int):
        assert SizeType(bytes_val).sectors == sectors

    @pytest.mark.parametrize(
        "bytes_val",
        [
            1,
            BYTES_PER_SECTOR - 1,
            5 * BYTES_PER_SECTOR + 1,
            5 * BYTES_PER_SECTOR - 1
        ]
    )
    def test_sectors_invalid(self, bytes_val: int):
        s = SizeType(bytes_val)
        with pytest.raises(Exception):
            s.sectors()


    @pytest.mark.parametrize(
        "left_bytes,right_bytes,expected",
        COMPARE_TABLE_LT
    )
    def test_compare_lt(self, left_bytes: Optional[int], right_bytes: Optional[int], expected: bool):
        if expected:
            assert SizeType(left_bytes) < SizeType(right_bytes)
        else:
            assert not SizeType(left_bytes) < SizeType(right_bytes)

    @pytest.mark.parametrize(
        "left_bytes,right_bytes,expected",
        COMPARE_TABLE_LE
    )
    def test_compare_le(self, left_bytes: Optional[int], right_bytes: Optional[int], expected: bool):
        if expected:
            assert SizeType(left_bytes) <= SizeType(right_bytes)
        else:
            assert not SizeType(left_bytes) <= SizeType(right_bytes)

    @pytest.mark.parametrize(
        "left_bytes,right_bytes,expected",
        COMPARE_TABLE_GT
    )
    def test_compare_gt(self, left_bytes: Optional[int], right_bytes: Optional[int], expected: bool):
        if expected:
            assert SizeType(left_bytes) > SizeType(right_bytes)
        else:
            assert not SizeType(left_bytes) > SizeType(right_bytes)

    @pytest.mark.parametrize(
        "left_bytes,right_bytes,expected",
        COMPARE_TABLE_GE
    )
    def test_compare_ge(self, left_bytes: Optional[int], right_bytes: Optional[int], expected: bool):
        if expected:
            assert SizeType(left_bytes) >= SizeType(right_bytes)
        else:
            assert not SizeType(left_bytes) >= SizeType(right_bytes)

    @pytest.mark.parametrize(
        "left_bytes,right_bytes,expected",
        COMPARE_TABLE_EQ
    )
    def test_compare_eq(self, left_bytes: Optional[int], right_bytes: Optional[int], expected: bool):
        if expected:
            assert SizeType(left_bytes) == SizeType(right_bytes)
        else:
            assert not SizeType(left_bytes) == SizeType(right_bytes)

    @pytest.mark.parametrize(
        "left_bytes,right_bytes,expected",
        COMPARE_TABLE_NE
    )
    def test_compare_ne(self, left_bytes: Optional[int], right_bytes: Optional[int], expected: bool):
        if expected:
            assert SizeType(left_bytes) != SizeType(right_bytes)
        else:
            assert not SizeType(left_bytes) != SizeType(right_bytes)


    def test_is_undefined(self):
        assert SizeType().is_undefined
        assert SizeType(None).is_undefined
        x = SizeType(1)
        x.bytes = None
        assert x.is_undefined

        assert not SizeType(1).is_undefined

    @pytest.mark.parametrize(
        "bytes_val, expected",
        [
            (None, "?"),
            (123,  f"0x{123:08x}"),
            (0,    f"0x{0:08x}")
        ]
    )
    def test_hex_bytes(self, bytes_val: int, expected: str):
        assert SizeType(bytes_val).hex_bytes == expected


    def test_repr(self):
        assert repr(SizeType()) == "None B"
        assert repr(SizeType(128)) == "128 B"


    @pytest.mark.parametrize(
        "left_bytes, right_bytes, expected_bytes",
        [
            (None, None, None),
            (None, 123, 123),
            (123, None, 123),
            (123, 123, 246)
        ]
    )
    def test_add(self, left_bytes: Optional[int], right_bytes: Optional[int], expected_bytes: int):
        assert SizeType(left_bytes) + SizeType(right_bytes) == SizeType(expected_bytes)

    @pytest.mark.parametrize(
        "left_bytes, right_bytes, expected_bytes",
        [
            (None, None, None),
            (None, 123, -123),
            (123, None, 123),
            (123, 123, 0)
        ]
    )
    def test_sub(self, left_bytes: Optional[int], right_bytes: Optional[int], expected_bytes: int):
        assert SizeType(left_bytes) - SizeType(right_bytes) == SizeType(expected_bytes)

    def test_bytes(self):
        with pytest.raises(Exception, match="SizeType.bytes called, when value is undefined"):
            SizeType().bytes

    def test_constructor(self):
        with pytest.raises(Exception, match="SizeType expects int, not str"):
            SizeType("abc")
        assert SizeType(None).is_undefined
        assert SizeType(1234).bytes == 1234
        assert SizeType(4096).sectors == 8
