# SPDX-License-Identifier: GPL-3.0-only

from typing import Optional
import re

BYTES_PER_SECTOR = 0x200
MULTIPLIER = {"k": 0x400, "M": 0x100000, "G": 0x40000000}


class SizeType:
    """A type to specify sizes in bytes and sectors

    This class can automatically parse string input as decimal
    or hexadecimal with a unit.
    Supported units are bytes (``B``) and Sectors (``S``) of 512 bytes.
    For bytes it also supports the SI prefixes for kilo (``k``),
    mega (``M``) and giga (``G``) with ``1 kB == 1024 B``.

    >>> SizeType(123).bytes
    123
    >>> SizeType(0).bytes
    0
    >>> SizeType().bytes is None
    True


    All comparison functions (``<,<=,>,>=,==,!=``) are implemented, 
    with ``None`` treaded as bigger than any non-``None`` value.

    >>> SizeType(1) > SizeType(0)
    True
    >>> SizeType(None) > SizeType(0)
    True
    >>> SizeType(None) > SizeType(None)
    False
    >>> SizeType(None) >= SizeType(None)
    True

    Some arithmetic functions are implemented as well.
    For these types None is treated as 0

    >>> SizeType(1) + SizeType(2) == SizeType(3)
    True
    >>> SizeType(1) + SizeType(None) == SizeType(1)
    True

    >>> SizeType(3) - SizeType(2) == SizeType(1)
    True
    >>> SizeType(3) - SizeType(None) == SizeType(3)
    True
    """

    _bytes: Optional[int]

    def __init__(self, bytes_val = None) -> None:
        self._bytes = bytes_val

    @classmethod
    def parse(cls, text: str):
        """Parses a size from the a string representation

        Examples:

        >>> SizeType.parse("0").bytes
        0
        >>> SizeType.parse("1 S").bytes
        512
        >>> SizeType.parse("0x10 S").bytes
        8192
        >>> SizeType.parse("5 MB").bytes
        5242880
        >>> SizeType.parse("").bytes
        Traceback (most recent call last):
        ...
        Exception: Invalid string: 
        """
        text = re.sub(r'\s', '', text)
        matches = re.match(r'(0x)?([0-9a-fA-F]+?)((?:[MkG]?B)|(?:S))?$', text)
        if not matches:
            raise Exception(f"Invalid string: {text}")

        prefix, value, unit = matches.groups()
        if not prefix:
            prefix = ""
        if value == "0":
            return cls(0)
        if not unit:
            raise Exception("no unit specified, and value is not 0")
        int_value = int(prefix + value, 0)
        if unit == "S":
            int_value *= BYTES_PER_SECTOR
        elif len(unit) > 1:
            int_value *= MULTIPLIER[unit[0]]
        return cls(int_value)

    @property
    def is_sector_aligned(self):
        """Return true, if this is aligned to a sector number"""
        return self._bytes % BYTES_PER_SECTOR == 0

    @property
    def sectors(self):
        """The sector number of this
        
        :raises: Exception if not sector aligned
        """
        if not self.is_sector_aligned:
            raise Exception(f"Cannot convert {self._bytes} B to sectors")
        return self._bytes // BYTES_PER_SECTOR

    @property
    def bytes(self):
        """The number of bytes"""
        return self._bytes

    @bytes.setter
    def bytes(self, bytes_val: int):
        self._bytes = bytes_val

    @property
    def hex_bytes(self) -> str:
        """The number of bytes as hex string with at least eight digits
        
        >>> SizeType(0x100).hex_bytes
        '0x00000100'
        >>> SizeType().hex_bytes
        '?'
        """
        return "?" if self.is_undefined else f"0x{self._bytes:08x}"

    def __repr__(self):
        return f"{self.bytes} B"

    @property
    def is_undefined(self) -> bool:
        """Returns true, if no value is set
        
        >>> SizeType().is_undefined
        True
        >>> SizeType(0).is_undefined
        False
        """
        return self._bytes is None

    def __eq__(self, other: 'SizeType') -> bool:
        return self._bytes == other._bytes

    def __ne__(self, other: 'SizeType') -> bool:
        return self._bytes != other._bytes

    def __lt__(self, other: 'SizeType') -> bool:
        if self.is_undefined:
            return False
        if other.is_undefined:
            return True
        return self.bytes < other.bytes

    def __gt__(self, other: 'SizeType') -> bool:
        if other.is_undefined:
            return False
        if self.is_undefined:
            return not other.is_undefined
        return self.bytes > other.bytes

    def __le__(self, other: 'SizeType') -> bool:
        return self == other or self < other

    def __ge__(self, other: 'SizeType') -> bool:
        return self == other or self > other


    def __add__(self, other: 'SizeType') -> 'SizeType':
        if self.is_undefined:
            return SizeType(other._bytes)
        if other.is_undefined:
            return SizeType(self._bytes)
        return SizeType(self._bytes + other._bytes)

    def __sub__(self, other: 'SizeType') -> 'SizeType':
        if self.is_undefined:
            if other.is_undefined:
                return SizeType(None)
            return SizeType(-other._bytes)
        if other.is_undefined:
            return SizeType(self._bytes)
        return SizeType(self._bytes - other._bytes)
