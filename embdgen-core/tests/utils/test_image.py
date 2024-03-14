# SPDX-License-Identifier: GPL-3.0-only

import pytest

from pathlib import Path
from io import BytesIO

from embdgen.core.utils.image import create_empty_image, copy_sparse, BuildLocation


def test_create_empty_image(tmp_path: Path):
    file_path = tmp_path / "test.img"
    create_empty_image(file_path, 10 * 1024 * 1024)
    stat = file_path.stat()
    assert stat.st_blocks == 0, "If the file is sparse, it has no blocks"
    assert stat.st_size == 10 * 1024 * 1024

def test_copy_sparse(tmp_path: Path):
    file_path = tmp_path / "test.img"
    create_empty_image(file_path, 1024 * 1024)

    some_data = b"\1" * 1024 + b"\0" * (4096 * 10) + b"\1" * 1024
    in_file = BytesIO(some_data)

    assert file_path.stat().st_blocks == 0

    with file_path.open("rb+") as out_file:
        copy_sparse(out_file, in_file, 1024)

    assert file_path.stat().st_size == 1024 * 1024

    with file_path.open("rb") as a_file:
        assert a_file.read(1024) == some_data[:1024]

    assert file_path.stat().st_blocks < (1024 * 1024) / file_path.stat().st_blksize, "The file is still sparse"

    # Now write the whole buffer into the file
    in_file = BytesIO(some_data)
    with file_path.open("rb+") as out_file:
        copy_sparse(out_file, in_file)

    with file_path.open("rb") as a_file:
        assert a_file.read(len(some_data)) == some_data

    assert file_path.stat().st_blocks < (1024 * 1024) / file_path.stat().st_blksize, "The file is still sparse"


def test_copy_sparse_deallocate(tmp_path: Path):
    file_path = tmp_path / "test.img"
    create_empty_image(file_path, 1024 * 1024)

    with file_path.open("rb+") as out_file:
        out_file.write(b"test")

    assert file_path.stat().st_blocks > 0

    in_file = BytesIO(b"\0" * 4096)
    with file_path.open("rb+") as out_file:
        copy_sparse(out_file, in_file)

    assert file_path.stat().st_blocks == 0

def test_copy_sparse_overflow(tmp_path: Path):
    file_path = tmp_path / "test.img"
    create_empty_image(file_path, 1024 * 1024)

    in_file = BytesIO(b"\0")
    with file_path.open("rb+") as out_file:
        with pytest.raises(Exception):
            copy_sparse(out_file, in_file, 100)

def test_copy_sparse_zero(tmp_path: Path):
    file_path = tmp_path / "test.img"
    create_empty_image(file_path, 1024 * 1024)

    in_file = BytesIO(b"")
    with file_path.open("rb+") as out_file:
        copy_sparse(out_file, in_file)
        assert out_file.tell() == 0

def test_copy_spares_after_end(tmp_path: Path):
    file_path = tmp_path / "test.img"
    create_empty_image(file_path, 4096)

    in_file = BytesIO(b"1" * 4096 + b"\0" * 4096 * 2)
    with file_path.open("rb+") as out_file:
        copy_sparse(out_file, in_file)
    assert file_path.stat().st_size == 4096 * 3

def test_get_temp_path():
    """ Just for 100% coverage"""
    assert isinstance(BuildLocation().get_path(), Path)
