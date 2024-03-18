# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import subprocess

import pytest

from embdgen.plugins.content.FilesContent import FilesContent
from embdgen.plugins.content.Fat32Content import Fat32Content
from embdgen.core.utils.image import BuildLocation
from embdgen.core.utils.SizeType import SizeType

class TestFat32Content:
    def test_files(self, tmp_path: Path):
        """
        Fat32 only supports files content right now
        """
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

        with pytest.raises(Exception, match="Fat32 regions require a fixed size at the moment"):
            obj.prepare()
        assert obj.size.is_undefined

        obj.size = SizeType.parse("10MB")
        obj.prepare()

        with image.open("wb") as out_file:
            obj.write(out_file)
        assert image.stat().st_size == SizeType.parse("10MB").bytes

        res = subprocess.run([
            "mdir",
            "-i", image,
            "-b"
        ], stdout=subprocess.PIPE, check=True, encoding="ascii")

        assert sorted(map(lambda x: x[3:], res.stdout.splitlines())) == sorted(map(lambda x: x.name, test_files))
