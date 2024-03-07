# SPDX-License-Identifier: GPL-3.0-only

import os
from pathlib import Path
import subprocess
from typing import Set
import pytest

from embdgen.core.utils.image import get_temp_path
from embdgen.plugins.content_generator.SplitArchiveContentGenerator import Split, SplitArchiveContentGenerator



def create_split(name: str, root: str, remove_root: bool = False) -> Split:
    s = Split()
    s.name = name
    s.root = root
    if remove_root:
        s.remove_root = True
    return s


def get_tree(base: Path) -> Set[str]:
    entries = set()
    for root, dirs, files in os.walk(base):
        rel = Path(root).relative_to(base)
        for entry in files + dirs:
            entries.add(str(rel / entry))
    return entries


def test_get_content_empty() -> None:
    obj = SplitArchiveContentGenerator()
    obj.name = "split"
    assert not list(obj.get_contents().keys())

def test_get_content_remaining() -> None:
    obj = SplitArchiveContentGenerator()
    obj.name = "split"
    obj.remaining = "remaining"
    assert list(obj.get_contents().keys()) == ['split.remaining']

def test_get_content_splits() -> None:
    obj = SplitArchiveContentGenerator()
    obj.name = "split"
    obj.remaining = "remaining"
    obj.splits = [
        create_split('split1', 'foo'),
        create_split('split2', 'bar')
    ]
    assert list(obj.get_contents().keys()) == ['split.split1', 'split.split2', 'split.remaining']

@pytest.fixture(scope="class")
def tmp_path_class(tmp_path_factory):
    return tmp_path_factory.mktemp("data")

archive_path: Path = None

class TestSplitArchiveContentGenerator:
    archive_path: Path

    @classmethod
    @pytest.fixture(autouse=True, scope='class')
    def setup_class(cls, tmp_path_factory):
        global archive_path
        tmp_path: Path = tmp_path_factory.mktemp("data")
        archive_path = tmp_path / "archive.tar"
        prep_dir = tmp_path / "prep"
        prep_dir.mkdir()

        mp1: Path = prep_dir / "mp1"
        mp1.mkdir()
        (mp1 / "mp1.file1").touch()
        (mp1 / "mp1.file2").touch()

        mp2: Path = prep_dir / "mp2"
        mp2.mkdir()
        (mp2 / "mp2.file1").touch()

        mp3: Path = prep_dir / "foobar" / "mp3"
        mp3.mkdir(parents=True)
        (mp3 / "mp3.file1").touch()
        (mp3 / "mp3.file2").touch()

        mp4: Path = prep_dir / "foobar" / "mp4"
        mp4.mkdir(parents=True)
        (mp4 / "mp4.file1").touch()
        (mp4 / "mp4.file2").touch()

        mp5: Path = prep_dir / "foobar" / "mp5"
        mp5.mkdir(parents=True)
        (mp5 / "mp5.file1").touch()
        (mp5 / "mp5.file2").touch()

        subprocess.run([
            "tar", "-cf", archive_path, "."
        ], cwd=prep_dir, check=True)

    def test_simple(self, tmp_path: Path):
        get_temp_path.TEMP_PATH = tmp_path

        obj = SplitArchiveContentGenerator()
        obj.name = "split"
        obj.archive = archive_path
        obj.remaining = "remaining"
        obj.splits = [
            create_split('split1', 'mp1'),
            create_split('split2', 'mp2'),
            create_split('split3', 'foobar/mp3', True)
        ]

        obj.splits[0].prepare()
        obj.splits[1].prepare() # This should do nothing


        assert set(map(lambda x: str(x.relative_to(Path(obj.splits[0].tmpDir.name))), obj.splits[0].files)) == set(["mp1.file1", "mp1.file2"])
        assert get_tree(Path(obj.splits[0].tmpDir.name)) == set(["mp1.file1", "mp1.file2"])
        assert get_tree(Path(obj.splits[1].tmpDir.name)) == set(["mp2.file1"])
        assert get_tree(Path(obj.splits[2].tmpDir.name)) == set(["mp3.file1", "mp3.file2"])
        assert get_tree(Path(obj._tmpDir.name)) == set([
            "mp1",
            "mp2",
            "foobar",
            "foobar/mp4",
            "foobar/mp4/mp4.file1",
            "foobar/mp4/mp4.file2",
            "foobar/mp5",
            "foobar/mp5/mp5.file1",
            "foobar/mp5/mp5.file2"
        ])

    def test_non_exisiting_split(self, tmp_path: Path):
        get_temp_path.TEMP_PATH = tmp_path

        obj = SplitArchiveContentGenerator()
        obj.name = "split"
        obj.archive = archive_path
        obj.splits = [
            create_split('split1', 'i-do-not-exist'),
        ]

        with pytest.raises(Exception, match="Path i-do-not-exist is not in archive .*archive.tar"):
            obj.splits[0].prepare()
