# SPDX-License-Identifier: GPL-3.0-only

import os
from pathlib import Path
import pytest

from embdgen.core.utils.FakeRoot import FakeRoot, subprocess

def get_uid_and_gid(fr: FakeRoot, file: Path) -> str:
    res = fr.run([
        "stat",
        "-c", "%u:%g",
        file
    ], stdout=subprocess.PIPE, encoding="utf-8")
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
