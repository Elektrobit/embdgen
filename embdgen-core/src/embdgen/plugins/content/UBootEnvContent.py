# SPDX-License-Identifier: GPL-3.0-only

from io import BufferedIOBase
from pathlib import Path
import struct
from typing import Dict, Optional
import zlib

from embdgen.core.content import BinaryContent
from embdgen.core.utils.class_factory import Config


@Config("vars")
@Config("file")
class UBootEnvContent(BinaryContent):
    """
    U-Boot Environment region

    The variables passed in using file and vars is merged
    with variables defined in vars overwriting variables
    defined in the variables file.
    """
    CONTENT_TYPE ="uboot_env"

    vars: Optional[Dict[str, str]] = None
    """Variables placed in the environment"""

    _file: Optional[Path] = None

    _data: bytes

    @property
    def file(self) -> Optional[Path]:
        """Variable file with key=value pairs"""
        return self._file

    @file.setter
    def file(self, value: Optional[Path]):
        if value and not value.exists():
            raise Exception(f"File {value} does not exist")
        self._file = value

    def _parse_file(self) -> Dict[str, str]:
        if not self.file:
            return {}
        out = {}
        with self.file.open() as f:
            for i, line in enumerate(f):
                line = line.strip()
                if line.startswith("#"):
                    continue
                parts = line.split("=", 1)
                if len(parts) != 2:
                    raise Exception(f"Invalid entry in U-Boot environment file (line {i + 1})")
                out[parts[0].strip()] = parts[1].strip()
        return out

    def _merged_vars(self) -> Dict[str, str]:
        out: Dict[str, str] = self._parse_file()

        if self.vars:
            out.update(self.vars)

        return out

    def prepare(self) -> None:
        if self.size.is_undefined:
            raise Exception("Size for U-Boot environment must be defined")

        self._data = b""

        res_vars = self._merged_vars()
        for key in sorted(res_vars.keys()):
            self._data += f"{key}={res_vars[key]}\0".encode()

        self._data += b"\0"

        if len(self._data) + 4 > self.size.bytes:
            overflow = 4 + len(self._data) - self.size.bytes
            raise Exception(f"U-Boot environment variables overflow storage area by {overflow} bytes")

        self._data += b"\xFF" * (self.size.bytes - len(self._data) - 4)
        self._data = struct.pack("<I", zlib.crc32(self._data)) + self._data

    def do_write(self, file: BufferedIOBase) -> None:
        file.write(self._data)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(...)"
