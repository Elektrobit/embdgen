# SPDX-License-Identifier: GPL-3.0-only

import os
from pathlib import Path
import subprocess
import dataclasses
from typing import List
import re
import stat
import pytest

from ..test_utils import SimpleCommandParser

from embdgen.plugins.content.Ext4Content import Ext4Content
from embdgen.plugins.content.FilesContent import FilesContent
from embdgen.plugins.content.ArchiveContent import ArchiveContent
from embdgen.core.utils.image import get_temp_file, BuildLocation
from embdgen.core.utils.SizeType import SizeType
from embdgen.core.utils.FakeRoot import FakeRoot

class DebugFs():

    class FileList(list):
        def assert_entry(self, names: List[str]):
            missing_names = names[:]

            for x in self:
                if x.name in missing_names:
                    missing_names.remove(x.name)

            if missing_names:
                assert missing_names == [], "No files missing"

    @dataclasses.dataclass
    class Entry():
        name: str
        mode: int
        uid: int
        gid: int
        size: int
        major: int
        minor: int
        link_to: str

        @property
        def is_dir(self) -> bool:
            return stat.S_ISDIR(self.mode)

        @property
        def is_reg(self) -> bool:
            return stat.S_ISREG(self.mode)

        @property
        def is_chr(self) -> bool:
            return stat.S_ISCHR(self.mode)

        @property
        def is_lnk(self) -> bool:
            return stat.S_ISLNK(self.mode)

    _image: Path

    def __init__(self, image: Path) -> None:
        self._image = image

    def ls(self, directory=".") -> FileList[Entry]:
        res = subprocess.run([
            "debugfs",
            "-R", f"ls -l {directory}",
            self._image
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf8")
        out =  []
        major = minor = 0
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            _, mode, _, uid, gid, size, date, time, name = re.split(r"\s+", line, maxsplit=8)
            if name == "." or name == "..":
                continue
            out.append(DebugFs.Entry(name, int(mode, base=8), int(uid), int(gid), int(size), major, minor, ""))
        return DebugFs.FileList(sorted(out, key=lambda x: x.name))

    def stat(self, path: str) -> Entry:
        res = subprocess.run([
            "debugfs",
            "-R", f"stat {path}",
            self._image
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf8")
        if not res.stdout:
            return None
        major = minor = 0
        link_to = ""
        for line in res.stdout.splitlines():
            line = line.strip()
            # EG: Inode: 12   Type: character special    Mode:  0664   Flags: 0x0
            m = re.search(r"Inode:\s+\d+\s+Type:\s+(.+?)\s+Mode:\s+(\d+)\s+Flags:\s+0x\d+", line)
            if m:
                mode = int(m.group(2), base=8)
                if m.group(1) == 'regular':
                    mode += stat.S_IFREG
                elif m.group(1) == 'directory':
                    mode += stat.S_IFDIR
                elif m.group(1) == 'symlink':
                    mode += stat.S_IFLNK
                elif m.group(1) == 'character special':
                    mode += stat.S_IFCHR
                else:
                    raise Exception(f"Unknown file type returned by debugfs stat '{m.group(1)}'.")
                continue
            # EG: User:   123   Group:   456   Size: 0
            # or: User:   123   Group:   456   Project:     0   Size: 0
            m = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)\s+(?:Project:\s+\d+\s+)?Size:\s+(\d+)", line)
            if m:
                uid = int(m.group(1))
                gid = int(m.group(2))
                size = int(m.group(3))
                continue
            # EG: (New-style) Device major/minor number: 291:1110 (hex 123:456)
            m = re.search(r"Device major/minor number:\s+(\d+):(\d+)", line)
            if m:
                major = int(m.group(1))
                minor = int(m.group(2))
            m = re.search(r"Fast link dest: \"(.+?)\"", line)
            if m:
                link_to = m.group(1)
        return DebugFs.Entry(Path(path).name, mode, uid, gid, size, major, minor, link_to)


class Tune2Fs(SimpleCommandParser):
    ATTRIBUTE_MAP = {
        "Block count": ("block_count", int),
        "Block size":  ("block_size", int),
        "Filesystem magic number": ("magic", lambda x: int(x, 16))
    }

    block_count: int = -1
    block_size: int = -1
    magic: int = -1

    def __init__(self, image: Path) -> None:
        super().__init__(["tune2fs", "-l", image])

    @property
    def size(self):
        return self.block_count * self.block_size



def test_from_files(tmp_path: Path):
    BuildLocation().set_path(tmp_path)

    image = tmp_path / "image"
    test_dir = tmp_path / "test_dir"

    test_dir.mkdir()
    (test_dir / "foobar").write_text("Hello world")
    (test_dir / "foobar.slnk").symlink_to("foobar")
    (test_dir / "dir").mkdir()
    (test_dir / "dir" / "a").write_text("Fooo")

    obj = Ext4Content()
    obj.content = FilesContent()
    obj.content.files = [test_dir / "*"]

    with pytest.raises(Exception, match="Ext4 content requires a fixed size at the moment"):
        obj.prepare()

    obj.size = SizeType.parse("10MB")
    obj.prepare()

    with image.open("wb") as out_file:
        obj.write(out_file)
    assert image.stat().st_size == SizeType.parse("10MB").bytes

    dfs = DebugFs(image)
    root_dir = dfs.ls()
    root_dir.assert_entry(["lost+found", "foobar", "foobar.slnk", "dir"])
    dfs.ls("dir").assert_entry(["a"])

    assert dfs.stat("foobar").uid == os.getuid()


def test_from_archive_fakeroot(tmp_path: Path):
    BuildLocation().set_path(tmp_path)

    image = tmp_path / "image"
    archive = tmp_path / "archive.tar"
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    sub_dir = test_dir / "sub_dir"
    sub_dir.mkdir()

    fr = FakeRoot(get_temp_file())

    fr.run([
        "mknod",
        test_dir / "node",
        "c",
        str(0x123), str(0x456)
    ])

    fr.run([
        "chown",
        "123:456",
        test_dir / "node"
    ])

    fr.run([
        "ln",
        "-s",
        "/var/run",
        test_dir / "abs_link",
    ])

    fr.run([
        "chown",
        "567:890",
        sub_dir
    ])

    fr.run([
        "mknod",
        sub_dir / "node",
        "c",
        str(0x123), str(0x456)
    ])

    fr.run([
        "chown",
        "123:456",
        sub_dir / "node"
    ])

    fr.run([
        "ln",
        "-s",
        "/var/run",
        sub_dir / "abs_link",
    ])

    fr.run([
        "tar",
        "-cf", archive,
        "."
    ], cwd=test_dir)

    obj = Ext4Content()
    obj.content = ArchiveContent()
    obj.content.archive = archive

    obj.size = SizeType.parse("10MB")
    obj.prepare()

    with image.open("wb") as out_file:
        obj.write(out_file)

    dfs = DebugFs(image)

    subdir_stat = dfs.stat("sub_dir")
    assert subdir_stat.uid == 567
    assert subdir_stat.gid == 890

    node_stat = dfs.stat("node")
    assert node_stat.uid == 123
    assert node_stat.gid == 456
    assert node_stat.is_chr
    assert node_stat.major == 0x123
    assert node_stat.minor == 0x456

    node_stat = dfs.stat("sub_dir/node")
    assert node_stat.uid == 123
    assert node_stat.gid == 456
    assert node_stat.is_chr
    assert node_stat.major == 0x123
    assert node_stat.minor == 0x456

    link_stat = dfs.stat("abs_link")
    assert link_stat.is_lnk
    assert link_stat.link_to == "/var/run"

    link_stat = dfs.stat("sub_dir/abs_link")
    assert link_stat.is_lnk
    assert link_stat.link_to == "/var/run"

def test_empty_ext4(tmp_path: Path) -> None:
    BuildLocation().set_path(tmp_path)
    image = tmp_path / "image"

    obj = Ext4Content()
    obj.size = SizeType.parse("100 MB")
    obj.prepare()

    with image.open("wb") as f:
        obj.write(f)

    tune2fs = Tune2Fs(image)
    assert tune2fs.ok
    assert tune2fs.size == SizeType.parse("100 MB").bytes
    assert tune2fs.magic == 0xEF53
