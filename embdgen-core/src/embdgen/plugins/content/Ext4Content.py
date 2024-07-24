# SPDX-License-Identifier: GPL-3.0-only

import io
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Optional

from embdgen.core.content.BinaryContent import BinaryContent
from embdgen.core.content.FilesContentProvider import FilesContentProvider
from embdgen.core.utils.class_factory import Config
from embdgen.core.utils.FakeRoot import FakeRoot
from embdgen.core.utils.image import (BuildLocation, copy_sparse,
                                      create_empty_image, get_temp_file)


@Config("content")
class Ext4Content(BinaryContent):
    """Ext4 Content
    """
    CONTENT_TYPE = "ext4"

    content: Optional[FilesContentProvider]
    """Files, that are added to the filesystem"""

    def __init__(self) -> None:
        super().__init__()
        self.content = None

    def prepare(self) -> None:
        if self.size.is_undefined:
            raise Exception("Ext4 content requires a fixed size at the moment")
        if self.content:
            self.content.prepare()

    def _prepare_result(self):
        create_empty_image(self.result_file, self.size.bytes)

        if self.content:
            with TemporaryDirectory(dir=BuildLocation().path) as diro:
                fr = FakeRoot(get_temp_file(), self.content.fakeroot)
                tmp_dir = Path(diro)
                for file in self.content.files:
                    fr.copy(file, tmp_dir)

                fr.run([
                    "mkfs.ext4",
                    "-d", diro,
                    self.result_file
                ], check=True)
        else:
            subprocess.run([
                "mkfs.ext4", self.result_file
            ], check=True)

    def do_write(self, file: io.BufferedIOBase):
        with open(self.result_file, "rb") as in_file:
            copy_sparse(file, in_file, self.size.bytes)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.content or ''})"
