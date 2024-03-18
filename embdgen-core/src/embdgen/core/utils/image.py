# SPDX-License-Identifier: GPL-3.0-only

"""
Utility functions for working with images
"""
from __future__ import annotations

import io
import os
import tempfile
import shutil

from pathlib import Path
from typing import Optional
from fallocate import fallocate, FALLOC_FL_PUNCH_HOLE, FALLOC_FL_KEEP_SIZE # type: ignore


class BuildLocation:
    """
    Temporary location of the builds
    """
    __instance: BuildLocation | None = None
    _path: Path
    _was_created: bool

    def __new__(cls) -> BuildLocation:
        if cls.__instance is None:
            cls.__instance: BuildLocation = super(BuildLocation, cls).__new__(cls)
            cls.__instance._path = Path(tempfile.mkdtemp(prefix="embdgen-"))
            cls.__instance._was_created = True
        return cls.__instance

    def __del__(self):
        self._remove()

    def set_path(self, path: Path) -> None:
        self._remove()
        self._path = path
        self._was_created = False
        if not self._path.exists():
            self._path.mkdir(parents=True, exist_ok=True)
            self._was_created = True

    def remove(self) -> None:
        self._remove()
        BuildLocation.__instance = None

    def _remove(self) -> None:
        if self._was_created and self._path.exists():
            shutil.rmtree(self._path)

    @property
    def path(self):
        return self._path


def create_empty_image(filename: Path, size: int) -> None:
    """
    Create an empty sparse (if possible) file
    """
    with open(filename, "wb") as out_file:
        out_file.truncate(size)

def copy_sparse(out_file: io.BufferedIOBase, in_file: io.BufferedIOBase, size: Optional[int]=None) -> None:
    """
    Copy sparse from in_file to out_file up to size bytes.
    This does not necessarily create the minimum sparse file.
    In the current implementation it only makes 4096 byte blocks of zeros sparse.
    If a block is shorter, it is actually written to the out_file.
    This is a time vs. space optimization. Checking if a fixed size block is empty can
    be implemented very fast in python, but checking if an arbitrarily long block is
    empty is not very efficient.
    """
    cur_pos = in_file.tell()
    max_size = in_file.seek(0, io.SEEK_END) - cur_pos
    in_file.seek(cur_pos)

    if not size:
        size = max_size
    elif size > max_size:
        raise Exception(f"Trying to copy {size} B, but the file has only {max_size} B left")

    zero_block = b"\0" * 4096
    def is_zero(block):
        """
        Note: if the block size is less than 4096, this will return False, but it just
        makes a part of the file non-sparse, which does not matter
        """
        return block == zero_block

    if size == 0:
        return

    to_copy = size
    while to_copy > 0:
        block_size = min(4096, to_copy)
        data = in_file.read(block_size)
        to_copy -= len(data)
        if not is_zero(data):
            out_file.write(data)
        else:
            # Deallocate blocks, to ensure they are 0
            fallocate(out_file, out_file.tell(), len(data), FALLOC_FL_PUNCH_HOLE + FALLOC_FL_KEEP_SIZE)
            out_file.seek(len(data), io.SEEK_CUR)

    # If there is a hole at the end of the file,
    # allocate the remainder of the file as a whole
    cur_pos = out_file.tell()
    out_file.seek(0, io.SEEK_END)
    if cur_pos > out_file.tell():
        out_file.seek(cur_pos - 1)
        out_file.write(b"\0")
        os.ftruncate(out_file.fileno(), cur_pos)
    else:
        out_file.seek(cur_pos)


def get_temp_file(ext: str="") -> Path:
    return Path(tempfile.mktemp(dir=BuildLocation().path, suffix=ext))
