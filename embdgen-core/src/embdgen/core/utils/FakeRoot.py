# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import shutil
import subprocess
from typing import Optional, List, Union


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
