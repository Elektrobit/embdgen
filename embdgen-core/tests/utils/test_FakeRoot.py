# SPDX-License-Identifier: GPL-3.0-only

import os
from pathlib import Path
import pytest
import stat

from embdgen.core.utils.FakeRoot import FakeRoot, subprocess

from ..test_utils.system import calc_umask

def get_uid_and_gid(fr: FakeRoot, file: Path) -> str:
    if not fr:
        fr = subprocess
    res = fr.run([
        "stat",
        "-c", "%u:%g",
        file
    ], stdout=subprocess.PIPE, encoding="utf-8", check=True)
    return res.stdout.strip()

def get_mode(fr: FakeRoot, file: Path) -> int:
    if not fr:
        fr = subprocess
    res = fr.run([
        "stat",
        "-c", "%a",
        file
    ], stdout=subprocess.PIPE, encoding="utf-8", check=True)
    return int(res.stdout, 8)

def get_node(fr: FakeRoot, file: Path) -> str:
    if not fr:
        fr = subprocess
    res = fr.run([
        "stat",
        "-c", "%f:%t:%T",
        file
    ], stdout=subprocess.PIPE, encoding="utf-8", check=True)
    mode, major, minor = map(lambda x: int(x, 16), res.stdout.strip().split(":"))
    mode = stat.filemode(mode)[0]
    return f"{mode}:{major}:{minor}"

def get_symlink(fr: FakeRoot, file: Path) -> str:
    if not fr:
        fr = subprocess
    res = fr.run([
        "readlink",
        file
    ], stdout=subprocess.PIPE, encoding="utf-8", check=True)
    return res.stdout.strip()

def test_simple(tmp_path: Path):
    savefile = tmp_path / "fakeroot.save"
    file1 = tmp_path / "file1"
    file2 = tmp_path / "file2"
    file3 = tmp_path / "file3"

    fr = FakeRoot(savefile)

    fr.run([
        "touch",
        file1, file2
    ])

    fr.run([
        "chown",
        "123:456",
        file1
    ])

    fr.run([
        "cp", "-p", file1, file3
    ])

    assert get_uid_and_gid(fr, file1) == "123:456"
    assert get_uid_and_gid(fr, file2) == "%d:%d" % (os.getuid(), os.getgid())
    assert get_uid_and_gid(fr, file3) == "123:456"



def test_inherit(tmp_path: Path):
    savefile1 = tmp_path / "fakeroot1.save"
    savefile2 = tmp_path / "fakeroot2.save"


    file1 = tmp_path / "file1"
    file2 = tmp_path / "file2"

    fr = FakeRoot(savefile1)

    fr.run([
        "touch",
        file1
    ])

    fr.run([
        "chown",
        "123:456",
        file1
    ])

    assert get_uid_and_gid(fr, file1) == "123:456"

    fr2 = FakeRoot(savefile2, fr)
    assert get_uid_and_gid(fr2, file1) == "123:456"


    fr.run([
        "cp", "-p", file1, file2
    ])

    assert get_uid_and_gid(fr, file2) == "123:456"


def test_run(tmp_path: Path):
    savefile1 = tmp_path / "fakeroot1.save"

    fr = FakeRoot(savefile1)

    with pytest.raises(subprocess.CalledProcessError):
        fr.run(["false"])

    fr.run(["false"], check=False)


def test_copy(tmp_path: Path):
    savefile1 = tmp_path / "fakeroot1.save"
    savefile2 = tmp_path / "fakeroot2.save"
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    fr = FakeRoot(savefile1)

    src.mkdir()

    fr.run(["chown", "678:900", src])
    fr.run(["chmod", "0712", src])
    fr.run(["touch", src / "file_a"])
    fr.run(["chmod", "ogu+rwxs", src / "file_a"])
    fr.run(["chown", "123:456", src / "file_a"])
    fr.run(["mknod", src / "node", "c", str(123), str(456)])

    fr.run(["ln", "-s", "/i/do/not/exist", src / "invalid_symlink"])

    os.mkfifo(src / "fifo", 0o621)
    fr.run(["chown", "666:999", src / "fifo"])


    fr2 = FakeRoot(savefile2, fr)

    fr2.copy(src, dst)
    fr2.copy(src / "file_a", dst)

    # A guaranteed device file
    fr2.copy("/dev/null", dst)
    fr2.copy("/dev/loop0", dst)

    # A guaranteed file on another filesystem, to trigger the copy instead of hardlink path
    fr2.copy("/proc/self/environ", dst)

    assert get_mode(fr2, dst / "src") == 0o712
    assert get_uid_and_gid(fr2, dst / "src") == "678:900"
    assert get_uid_and_gid(fr2, dst / "src/file_a") == "123:456"

    assert get_uid_and_gid(fr2, dst / "file_a") == "123:456"
    assert get_mode(fr2, dst / "file_a") == 0o6777

    assert get_uid_and_gid(fr2, dst / "src/node") == "0:0"
    assert get_node(fr2, dst / "src/node") == "c:123:456"

    assert get_symlink(fr2, dst / "src/invalid_symlink") == "/i/do/not/exist"

    assert get_node(fr2, dst / "src/fifo") == "p:0:0"
    assert get_mode(fr2, dst / "src/fifo") == calc_umask(0o621)
    assert get_uid_and_gid(fr2, dst / "src/fifo") == "666:999"

    assert get_mode(fr2, dst / "null") == get_mode(None, "/dev/null")
    assert get_node(fr2, dst / "null") == get_node(None, "/dev/null")
    assert get_uid_and_gid(fr2, dst / "null") == get_uid_and_gid(None, "/dev/null")

    assert get_mode(fr2, dst / "loop0") == get_mode(None, "/dev/loop0")
    assert get_node(fr2, dst / "loop0") == get_node(None, "/dev/loop0")
    assert get_uid_and_gid(fr2, dst / "loop0") == get_uid_and_gid(None, "/dev/loop0")

    assert (dst / "environ").exists()
    assert (dst / "environ").is_file()
    assert (dst / "environ").stat().st_size != 0
