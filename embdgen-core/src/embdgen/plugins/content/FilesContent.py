# SPDX-License-Identifier: GPL-3.0-only

from typing import List
from pathlib import Path

from embdgen.core.utils.class_factory import Config
from embdgen.core.content.FilesContentProvider import FilesContentProvider

@Config("files")
class FilesContent(FilesContentProvider):
    """A list of files
    
    It is up to the including content module, to decide what happens with the files.
    """
    CONTENT_TYPE = "files"

    _files: List[Path]
    _configured_files: List[Path]


    def __init__(self):
        super().__init__()
        self.files = []
        self._configured_files = []

    @property
    def files(self) -> List[Path]:
        """The list of files
        Wildcards are allowed and expanded using python glob module.
        Note that you probably only want one glob for a directory like `dir/*`.
        This will include all files including the directory structure under and excluding `dir`.
        """
        return self._files

    @files.setter
    def files(self, files: List[Path]) -> None:
        self._configured_files = files
        self._files = []
        for p in files:
            self._files += p.parent.glob(p.name)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(map(str, self._configured_files))})"
