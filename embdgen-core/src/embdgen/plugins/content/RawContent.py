# SPDX-License-Identifier: GPL-3.0-only

from io import BufferedIOBase
from pathlib import Path
from typing import Optional

from embdgen.core.utils.class_factory import Config
from embdgen.core.content.BinaryContent import BinaryContent
from embdgen.core.utils.SizeType import SizeType
from embdgen.core.utils.image import copy_sparse

@Config('file')
@Config("offset", optional=True)
class RawContent(BinaryContent):
    """Raw binary content

    It is up to the including content module, to decide what happens with the files.
    """
    CONTENT_TYPE = "raw"

    _file: Path
    _offset: SizeType

    __file_size: Optional[int] = None

    def __init__(self) -> None:
        super().__init__()
        self.offset = SizeType(0)

    @property
    def file(self) -> Path:
        """Path of the raw content file"""
        return self._file

    @file.setter
    def file(self, value: Path):
        new_file_size = value.stat().st_size
        if self._offset.bytes > new_file_size:
            raise Exception(f"Offset {self._offset.hex_bytes} B outside of file {value}")
        self.__file_size = new_file_size
        self._file = value

    @property
    def offset(self) -> SizeType:
        """Offset into the input file.

        This can be used, if the file has a header, that should be skipped.

        In combination with RawRegion's size attribute, this can also be used,
        to copy a specific part of a fle to the resulting image.
        """
        return self._offset

    @offset.setter
    def offset(self, value: SizeType):
        if self.__file_size is not None and value.bytes > self.__file_size:
            raise Exception(f"Offset {value.hex_bytes} B outside of file {self.file}")
        self._offset = value

    def prepare(self) -> None:
        file_size_available = self.__file_size
        file_size_available -= self.offset.bytes # type: ignore[operator]
        if self.size.is_undefined:
            self.size = SizeType(file_size_available)

    def do_write(self, file: BufferedIOBase):
        with open(self.file, "rb") as in_file:
            in_file.seek(self.offset.bytes)
            copy_sparse(file, in_file, self.size.bytes)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.file}@{self.offset.hex_bytes})"
