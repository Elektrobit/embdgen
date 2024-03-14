# SPDX-License-Identifier: GPL-3.0-only

from tempfile import TemporaryDirectory
from typing import Dict, List, Optional
from pathlib import Path

from embdgen.core.content.BaseContent import BaseContent
from embdgen.core.content.FilesContentProvider import FilesContentProvider
from embdgen.core.utils.FakeRoot import FakeRoot

from embdgen.core.utils.class_factory import Config

from embdgen.core.content_generator.BaseContentGenerator import BaseContentGenerator
from embdgen.core.utils.image import BuildLocation
from embdgen.plugins.content.ArchiveContent import ArchiveContent


@Config("name")
@Config("root")
@Config("remove_root", optional=True)
class Split(FilesContentProvider):
    """Split for a SplitArchiveContentGenerator
    """

    name: str = ""
    """Name of this split"""

    root: str
    """Root directory of this split in the archive"""

    remove_root: bool = False
    """If set to true, the root directory of the split is removed from the remaining tree"""

    base: ArchiveContent
    _tmpDir: Optional[TemporaryDirectory] = None

    @property
    def tmpDir(self) -> TemporaryDirectory:
        if not self._tmpDir:
            self._tmpDir = TemporaryDirectory(  # pylint: disable=consider-using-with
                dir=BuildLocation().get_path()
            )
        return self._tmpDir

    def init(self, base: "SplitArchiveContentGenerator", fakeroot: FakeRoot):
        self._fakeroot = fakeroot
        self.base = base

    def prepare(self) -> None:
        self.base.prepare()

    @property
    def files(self) -> List[Path]:
        return list(Path(self.tmpDir.name).iterdir())

    def __repr__(self) -> str:
        return f"Split({self.name}, {self.root})"

@Config("archive")
@Config("splits")
@Config("remaining", optional=True)
class SplitArchiveContentGenerator(BaseContentGenerator, ArchiveContent):
    """Split an archive into multiple parts

    This can be used to create multiple content modules from a single archive.
    Each split can define up to one root directory. The content of that directory
    is moved to the split and the directory is kept as an empty directory (that can be used as a mountpoint later).
    """
    CONTENT_TYPE = "split_archive"

    archive: Path
    """Archive to be unpacked"""

    _splits: List[Split]

    remaining: Optional[str] = None
    """Name of the remaining content"""

    def __init__(self) -> None:
        super().__init__()
        self.splits = []

    def get_contents(self) -> Dict[str, BaseContent]:
        out: Dict[str, BaseContent] = {
            f"{self.name}.{s.name}": s for s in self.splits
        }

        if self.remaining:
            out[f"{self.name}.{self.remaining}"] = self
        return out

    def prepare(self) -> None:
        if self._tmpDir:
            return
        super().prepare()
        tmpDir = Path(self._tmpDir.name) # type: ignore[union-attr]

        for s in self.splits:
            if not (tmpDir / s.root).is_dir():
                raise Exception(f"Path {s.root} is not in archive {self.archive}")
            for entry in (tmpDir / s.root).iterdir():
                s.fakeroot.run([
                    "mv",
                    entry,
                    s.tmpDir.name
                ], check=True)
            if s.remove_root:
                s.fakeroot.run([
                    "rmdir", tmpDir / s.root
                ], check=True)

        self._files = list(tmpDir.iterdir())

    @property
    def splits(self) -> List[Split]:
        """List of splits"""
        return self._splits

    @splits.setter
    def splits(self, splits: List[Split]):
        for s in splits:
            s.init(self, self._fakeroot)
        self._splits = splits

    def __repr__(self) -> str:
        return f"SplitArchiveContentGenerator({self.name}: {', '.join(map(repr, self.splits))})"
