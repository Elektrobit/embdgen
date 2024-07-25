# SPDX-License-Identifier: GPL-3.0-only

import io
import subprocess
from typing import Optional

from embdgen.core.content.BinaryContent import BinaryContent
from embdgen.core.content.FilesContentProvider import FilesContentProvider
from embdgen.core.utils.class_factory import Config
from embdgen.core.utils.image import copy_sparse, create_empty_image


@Config("content")
@Config("size", optional=True)
class Fat32Content(BinaryContent):
    """Fat32 Content

    Currently this can only be created using a FilesContent,
    that contains a list of files, that are copied to the root
    of a newly created fat32 filesystem.
    """
    CONTENT_TYPE = "fat32"

    content: Optional[FilesContentProvider]
    """Content of this region"""

    def __init__(self) -> None:
        super().__init__()
        self.content = None

    def prepare(self) -> None:
        if self.size.is_undefined:
            raise Exception("Fat32 content requires a fixed size at the moment")
        if self.content:
            self.content.prepare()


    def _prepare_result(self):
        create_empty_image(self.result_file, self.size.bytes)

        subprocess.run([
                "mkfs.vfat",
                self.result_file
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        if self.content:
            for file in self.content.files:
                self.content.fakeroot.run(
                    [
                        "mcopy",
                        "-i", self.result_file,
                        file, "::"
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )


    def do_write(self, file: io.BufferedIOBase):
        with open(self.result_file, "rb") as in_file:
            copy_sparse(file, in_file, self.size.bytes)


    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(map(str, self.content.files)) if self.content else ''})"
