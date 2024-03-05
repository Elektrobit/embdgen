# SPDX-License-Identifier: GPL-3.0-only

from io import BufferedIOBase
from pathlib import Path
import subprocess

from embdgen.core.utils.SizeType import SizeType, BYTES_PER_SECTOR
from embdgen.core.utils.class_factory import Config
from embdgen.core.content.BinaryContent import BinaryContent
from embdgen.core.utils.image import create_empty_image, copy_sparse

@Config('content')
@Config('add_space', optional=True)
class ResizeExt4Content(BinaryContent):
    """Resize an ext4 partition
    
    Allows increasing the size of an ext4 filesystem
    """
    CONTENT_TYPE = "resize_ext4"

    content: BinaryContent
    """Content to resize"""

    _add_space: SizeType = SizeType(0)

    _tmpfile: Path

    @property
    def add_space(self) -> SizeType:
        """Space to add.
        
        This must be a multiple of the sector size (see: ``SizeType``)"""
        return self._add_space

    @add_space.setter
    def add_space(self, value: SizeType):
        if not value.is_sector_aligned:
            raise Exception(f"add_space must be a multiple of the sector size ({BYTES_PER_SECTOR} B)")
        self._add_space = value

    def prepare(self) -> None:
        self.content.prepare()
        self.size = self.content.size
        self.size += self.add_space

    def _prepare_result(self):
        create_empty_image(self.result_file, self.size.bytes)

        with self.result_file.open("rb+") as f:
            self.content.write(f)

        subprocess.run([
            "e2fsck",
            "-fp",
            str(self.result_file)
        ], check=True)

        subprocess.run([
            "resize2fs",
            str(self.result_file),
            f"{self.size.sectors}s"
        ], check=True)

    def do_write(self, file: BufferedIOBase):
        with self.result_file.open("rb") as in_file:
            copy_sparse(file, in_file)
