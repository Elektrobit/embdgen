# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import subprocess

import pytest

from ..test_utils import SimpleCommandParser

from embdgen.plugins.content.FilesContent import FilesContent
from embdgen.plugins.content.Fat32Content import Fat32Content
from embdgen.core.utils.image import BuildLocation
from embdgen.core.utils.SizeType import SizeType


class MInfo(SimpleCommandParser):
    ATTRIBUTE_MAP =  {
        "sector size": ("sector_size", lambda x: int(x.split()[0])),
        "big size": ("sectors", lambda x: int(x.split()[0])),
        "disk type": ("disk_type", lambda x: x[1:-1].strip())
    }

    sectors: int = -1
    sector_size: int = -1
    disk_type: str = ""

    def __init__(self, image: Path) -> None:
        super().__init__(["minfo", "-i", image])

    @property
    def size(self) -> int:
        return self.sectors * self.sector_size


class TestFat32Content:
    def test_files(self, tmp_path: Path):
        BuildLocation().set_path(tmp_path)

        image = tmp_path / "image"

        test_files = []
        for i in range(5):
            filename = tmp_path / f"test_file.{i}"
            filename.write_text(f"Test file #{i}")
            test_files.append(filename)

        obj = Fat32Content()
        obj.content = FilesContent()
        obj.content.files = test_files

        with pytest.raises(Exception, match="Fat32 content requires a fixed size at the moment"):
            obj.prepare()
        assert obj.size.is_undefined

        obj.size = SizeType.parse("32MB")
        obj.prepare()

        with image.open("wb") as out_file:
            obj.write(out_file)
        assert image.stat().st_size == SizeType.parse("32MB").bytes

        res = subprocess.run([
            "mdir",
            "-i", image,
            "-b"
        ], stdout=subprocess.PIPE, check=True, encoding="ascii")

        assert sorted(map(lambda x: x[3:], res.stdout.splitlines())) == sorted(map(lambda x: x.name, test_files))

    def test_empty(self, tmp_path: Path) -> None:
        BuildLocation().set_path(tmp_path)
        image = tmp_path / "image"

        obj = Fat32Content()
        obj.size = SizeType.parse("100 MB")
        obj.prepare()

        with image.open("wb") as out_file:
            obj.write(out_file)

        minfo = MInfo(image)
        assert minfo.ok, minfo.error

    def test_type_small(self, tmp_path: Path) -> None:
        BuildLocation().set_path(tmp_path)
        image = tmp_path / "image"

        obj = Fat32Content()
        obj.size = SizeType.parse("10 MB")
        obj.prepare()

        with image.open("wb") as out_file:
            obj.write(out_file)

        minfo = MInfo(image)
        assert minfo.ok, minfo.error
        assert minfo.disk_type == "FAT32"
