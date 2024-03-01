# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations
from typing import Any, Optional

from pathlib import Path
import subprocess

class FakeRoot():
    """
    Encapsulate usage of fakeroot command line tool

    This allows file operations, that are usually only possible with root rights
    (e.g setting owner/group and creating device nodes).
    The files are created on the filesystem just like normal files and the attributes,
    that cannot be set directly are recorded in a state database.
    This can be used to create e.g. device nodes, that are later read by an archive tool
    or by a filesystem creator, where creating files with these attributes is allowed.

    This class provides the run-method with the same syntax as subprocess run and automatically
    wraps all executions into fakeroot.

    A fakeroot can reuse the state file of another fakeroot without modifying it.
    """
    _savefile: Path
    _parent: Optional[FakeRoot]

    def __init__(self, savefile: Path, parent: "FakeRoot" = None) -> None:
        self._savefile = savefile
        self._parent = parent
        if parent and parent._parent:
            raise Exception("FakeRoot parent has already a parent. Recursive parenting is not allowed.")

    @property
    def savefile(self) -> Path:
        return self._savefile

    def run(self, args, **kwargs):
        check = True
        if "check" in kwargs:
            check = kwargs["check"]
            del kwargs["check"]

        safe_file = []
        if self._parent and self._parent.savefile.exists():
            safe_file = ["-i", self._parent.savefile]
        elif self._savefile.exists():
            safe_file = ["-i", self.savefile]

        return subprocess.run([
            "fakeroot",
            "-u", # Use -u, to prevent that all files are created as root
            "-s", self._savefile,
            *safe_file,
            "--",
            *args
        ], check=check, **kwargs)
