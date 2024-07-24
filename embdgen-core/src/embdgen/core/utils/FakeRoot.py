# SPDX-License-Identifier: GPL-3.0-only

from collections import deque
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from typing import Deque, Iterable, Optional, Tuple, List, Union


class FakeRoot():
    """Encapsulate usage of fakeroot command line tool

    This allows file operations, that are usually only possible with root rights
    (e.g setting owner/group and creating device nodes).
    The files are created on the filesystem just like normal files and the attributes,
    that cannot be set directly are recorded in a state database.
    This can be used to create e.g. device nodes, that are later read by an archive tool
    or by a filesystem creator, where creating files with these attributes is allowed.

    This class provides the run-method with the same syntax as subprocess run and automatically
    wraps all executions into fakeroot.

    A fakeroot can import the state file of another fakeroot without modifying it.
    """
    _savefile: Path

    def __init__(self, savefile: Path, parent: Optional["FakeRoot"] = None):
        self._savefile = savefile
        if parent and parent._savefile.exists():
            shutil.copyfile(parent._savefile, self._savefile)

    @property
    def savefile(self) -> Path:
        return self._savefile

    def run(self, args: List[Union[str, Path]], **kwargs):
        """
        Run a process in fakeroot.
        This is a wrapper for subprocess.run and works exactly the same with two exceptions:
        1. args can only be passed in as a list
        2. check defaults to true
        """
        check = True
        if "check" in kwargs:
            check = kwargs["check"]
            del kwargs["check"]

        safe_file: List[Union[str, Path]] = []
        if self._savefile.exists():
            safe_file = ["-i", self.savefile]

        return subprocess.run([
            "fakeroot",
            "-u", # Use -u, to prevent that all files are created as root
            "-s", self._savefile,
            *safe_file,
            "--",
            *args
        ], check=check, **kwargs)


    def copy(self, src: Path, dest: Path)-> None:
        """
        Copy a file or a directory tree from src to dest.

        dest is always a directory and created if it does not exist.
        The copying is done under fakeroot, to preserve all attributes.
        Symlinks in src (or if src is a symlink) are preserved in dest with
        the same target.
        Files are either hardlinked, if possible, or copied.
        """
        mod_self = sys.modules[__name__].__spec__
        if not mod_self: # pragma: no cover
            raise Exception("Cannot determine the module name of FakeRoot")
        dest.mkdir(parents=True, exist_ok=True)
        self.run([
            sys.executable,
            "-m", mod_self.name,
            src, dest
        ])

def copy_recursive(src_: Path, dest_: Path):
    to_do: Deque[Tuple[Iterable[Path], Path]] = deque([([src_], dest_)])

    def copy_attrs(src: Path, dest: Path, sstat: os.stat_result) -> None:
        shutil.copystat(src, dest)
        os.chown(dest, sstat.st_uid, sstat.st_gid)

    while to_do:
        srcs, dest_root = to_do.popleft()
        for src in srcs:
            dest = dest_root / src.name
            sstat: os.stat_result = src.lstat()

            if stat.S_ISLNK(sstat.st_mode):
                dest.symlink_to(src.readlink())
            elif stat.S_ISDIR(sstat.st_mode):
                dest.mkdir(exist_ok=True)
                copy_attrs(src, dest, sstat)
                to_do.append((list(src.iterdir()), dest))
            elif stat.S_ISCHR(sstat.st_mode) or stat.S_ISBLK(sstat.st_mode) or stat.S_ISFIFO(sstat.st_mode):
                os.mknod(dest, sstat.st_mode, sstat.st_rdev)
                copy_attrs(src, dest, sstat)
            elif stat.S_ISREG(sstat.st_mode):
                try:
                    os.link(src, dest)
                except OSError:
                    # Fallback to copy, if hardlink does not work
                    shutil.copyfile(src, dest)
                    copy_attrs(src, dest, sstat)
            else: # pragma: no cover
                raise Exception(f"Unable to copy {src}, unknown file type: {sstat.st_mode}")

def copy_main() -> int:
    if len(sys.argv) != 3: # pragma: no cover
        print("invalid arg count:", sys.argv)
        return 1

    src = Path(sys.argv[1])
    dest = Path(sys.argv[2])
    copy_recursive(src, dest)
    return 0

if __name__ == "__main__":
    sys.exit(copy_main())
