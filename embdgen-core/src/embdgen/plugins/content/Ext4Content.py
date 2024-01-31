# SPDX-License-Identifier: GPL-3.0-only

import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

from embdgen.core.utils.class_factory import Config
from embdgen.core.content.BinaryContent import BinaryContent
from embdgen.plugins.content.FilesContent import FilesContent
from embdgen.core.utils.image import create_empty_image, copy_sparse, get_temp_path


@Config("content")
class Ext4Content(BinaryContent):
    """Ext4 Content
    """
    CONTENT_TYPE = "ext4"

    content: FilesContent = None
    """Files, that are added to the filesystem"""

    def prepare(self) -> None:
        super().prepare()
        self.content.prepare()
        if self.size.is_undefined:
            raise Exception("Ext4 content requires a fixed size at the moment")

    def _prepare_result(self):
        create_empty_image(self.result_file, self.size.bytes)

        with TemporaryDirectory(dir=get_temp_path()) as diro:
            tmp_dir = Path(diro)
            for file in self.content.files:
                if file.is_dir():
                    shutil.copytree(file, Path(tmp_dir) / file.name, dirs_exist_ok=True, copy_function=os.link)
                else:
                    os.link(str(file), str(Path(tmp_dir) / file.name))

            subprocess.run([
                "mkfs.ext4",
                "-d", diro,
                self.result_file
            ], check=True)


    def do_write(self, file: io.BufferedIOBase):
        with open(self.result_file, "rb") as in_file:
            copy_sparse(file, in_file, self.size.bytes)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.content})"
