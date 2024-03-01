# SPDX-License-Identifier: GPL-3.0-only

import abc
from typing import List
from pathlib import Path

from embdgen.core.utils.FakeRoot import FakeRoot
from embdgen.core.utils.image import get_temp_file
from embdgen.core.content.BaseContent import BaseContent


class FilesContentProvider(BaseContent, abc.ABC):
    """Base class for all content providers, that provide a list of files"""

    _fakeroot: FakeRoot

    def __init__(self) -> None:
        super().__init__()
        self._fakeroot = FakeRoot(get_temp_file())

    @property
    def fakeroot(self) -> FakeRoot:
        return self._fakeroot

    @property
    @abc.abstractmethod
    def files(self) -> List[Path]:
        pass
