# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
from typing import Optional
import io
import abc

from ..utils.image import get_temp_file, copy_sparse

from .BaseContent import BaseContent


class BinaryContent(BaseContent):
    """
    Base class for content, that support writing directly to an image file
    """

    _result_file: Optional[Path] = None

    @property
    def result_file(self) -> Path:
        if not self._result_file:
            self._result_file = get_temp_file(ext=f".{self.__class__.__name__}")
            self._prepare_result()
        return self._result_file

    def write(self, file: io.BufferedIOBase) -> None:
        if self._result_file:
            with self.result_file.open("rb") as in_file:
                copy_sparse(file, in_file)
        else:
            self.do_write(file)

    def _prepare_result(self):
        with self._result_file.open("wb") as f:
            self.do_write(f)

    @abc.abstractmethod
    def do_write(self, file: io.BufferedIOBase) -> None:
        pass
