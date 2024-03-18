# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import subprocess
import re
import pytest

from embdgen.plugins.content.ResizeExt4Content import ResizeExt4Content
from embdgen.plugins.content.RawContent import RawContent
from embdgen.core.utils.image import create_empty_image, BuildLocation
from embdgen.core.utils.SizeType import SizeType


def get_ext4_size(filename: Path) -> int:
    res = subprocess.run([
        'tune2fs',
        '-l',
        str(filename)
    ], check=True, stdout=subprocess.PIPE, encoding="utf-8")

    data = {
        a[0].strip().lower() : a[1].strip()
            for a in map(lambda x: x.split(":", 1), res.stdout.splitlines())
            if len(a) == 2
    }
    return int(data.get('block count', 0)) * int(data.get('block size', 0))

class TestResizeExt4:
    def test_resize_0(self, tmp_path: Path):
        BuildLocation().set_path(tmp_path)
        test_fs = tmp_path / "ext4.img"

        create_empty_image(str(test_fs), 10 * 1024 * 1024)
        subprocess.run([
            'mkfs.ext4',
            str(test_fs)
        ], check=True)

        obj = ResizeExt4Content()
        obj.content = RawContent()
        obj.content.file = test_fs

        obj.prepare()

        output = tmp_path / "image.img"

        with output.open("wb") as f:
            obj.write(f)

        assert output.stat().st_size == test_fs.stat().st_size

        assert get_ext4_size(output) == get_ext4_size(test_fs), "Filesystem was not resized"

    def test_resize(self, tmp_path: Path):
        BuildLocation().set_path(tmp_path)
        test_fs = tmp_path / "ext4.img"

        create_empty_image(str(test_fs), 10 * 1024 * 1024)
        subprocess.run([
            'mkfs.ext4',
            str(test_fs)
        ], check=True)

        obj = ResizeExt4Content()
        obj.content = RawContent()
        obj.content.file = test_fs
        obj.add_space = SizeType.parse("10MB")

        obj.prepare()

        output = tmp_path / "image.img"

        with output.open("wb") as f:
            obj.write(f)

        assert output.stat().st_size == test_fs.stat().st_size + 10 * 1024 * 1024

        assert get_ext4_size(output) == test_fs.stat().st_size + 10 * 1024 * 1024, "Filesystem was resized"

    def test_unaligned(self):
        obj = ResizeExt4Content()
        with pytest.raises(Exception, match=re.escape("add_space must be a multiple of the sector size (512 B)")):
            obj.add_space = SizeType(511)
