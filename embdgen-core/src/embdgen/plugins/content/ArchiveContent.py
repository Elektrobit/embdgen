# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
from typing import List, Optional
from tempfile import TemporaryDirectory

from embdgen.core.utils.class_factory import Config
from embdgen.core.content.FilesContentProvider import FilesContentProvider
from embdgen.core.utils.image import BuildLocation

@Config("archive")
class ArchiveContent(FilesContentProvider):
    """Content from an archive"""

    CONTENT_TYPE = "archive"

    archive: Path
    """Archive to be unpacked"""

    _files: List[Path]
    _tmpDir: Optional[TemporaryDirectory] = None

    @property
    def files(self) -> List[Path]:
        return self._files or []

    def prepare(self) -> None:
        self._tmpDir = TemporaryDirectory(  # pylint: disable=consider-using-with
            dir=BuildLocation().get_path()
        )
        tmpDir = Path(self._tmpDir.name)

        self._fakeroot.run([
            "tar",
            "-xpf", self.archive,
            "-C", tmpDir
        ], check=True)

        self._files = list(tmpDir.iterdir())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.archive})"
