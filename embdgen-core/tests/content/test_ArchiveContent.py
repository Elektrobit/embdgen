# SPDX-License-Identifier: GPL-3.0-only

from functools import lru_cache
import os
from pathlib import Path
import subprocess

from embdgen.plugins.content.ArchiveContent import ArchiveContent
from embdgen.core.utils.image import get_temp_path
from embdgen.core.utils.FakeRoot import FakeRoot

@lru_cache
def cur_umask() -> int:
    tmp = os.umask(0o022)
    os.umask(tmp)
    return tmp

def calc_umask(mode: int) -> str:
    mode = mode & ~cur_umask()
    return f"{mode:o}"

def test_simple(tmp_path: Path):
    get_temp_path.TEMP_PATH = tmp_path
    
    prepare_dir = tmp_path / "prepare"
    archive = tmp_path / "archive.tar"

    prepare_dir.mkdir()
    (prepare_dir / "foo").write_text("foo")
    (prepare_dir / "bar").mkdir()
    (prepare_dir / "bar" / "a").touch()
    (prepare_dir / "bar" / "b").touch()

    subprocess.run([
        "tar",
        "-cf",
        archive,
        "."
    ], check=True, cwd=prepare_dir)


    obj = ArchiveContent()
    obj.archive = archive
    obj.prepare()

    assert sorted(map(lambda x: x.name, obj.files)) == ["bar", "foo"]


def test_fakeroot(tmp_path: Path):
    get_temp_path.TEMP_PATH = tmp_path

    save_file = tmp_path / "fakeroot.save"
    prepare_dir = tmp_path / "prepare"
    archive = tmp_path / "archive.tar"

    prepare_dir.mkdir()
    (prepare_dir / "foo").write_text("foo")
    (prepare_dir / "bar").mkdir()
    (prepare_dir / "a").touch()
    (prepare_dir / "bar" / "b").touch()


    fr = FakeRoot(save_file)

    fr.run([
        "chown",
        "123:456",
        prepare_dir / "a"
    ])

    fr.run([
        "chmod",
        "0777",
        prepare_dir / "a"
    ])

    fr.run([
        "mknod",
        prepare_dir / "node",
        "c", str(0x123), str(0x456)
    ])

    fr.run([
        "tar",
        "-cf",
        archive,
        "."
    ], cwd=prepare_dir)

    obj = ArchiveContent()
    obj.archive = archive
    obj.prepare()

    res = obj.fakeroot.run(["stat", "-c", "%n:%u:%g:%a:%t:%T", *obj.files], stdout=subprocess.PIPE, encoding="utf8")

    # Output: lines of "/path/to/file/node:0:0:664:123:456"
    # 1. Split away all path components, leaving only the name
    # 2. Split at colon
    # resulting in list of 6-tuple:
    #  - name
    #  - uid
    #  - gid
    #  - access mode
    #  - minor device node
    #  - major device node

    files = sorted(map(lambda x: x.split("/")[-1].split(":"), res.stdout.splitlines()), key=lambda x: x[0])

    uid, gid = map(str, (os.getuid(), os.getgid()))

    assert files == [
        ['a',    '123', '456', '777', '0',   '0'],
        ['bar',  uid,   gid,   calc_umask(0o777), '0',   '0'],
        ['foo',  uid,   gid,   calc_umask(0o666), '0',   '0'],
        ['node', '0',   '0',   calc_umask(0o666), '123', '456']
    ]
