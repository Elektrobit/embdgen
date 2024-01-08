from pathlib import Path
import io
import abc

from embdgen.core.utils.image import get_temp_file, copy_sparse

from .BaseContent import BaseContent


class BinaryContent(BaseContent):
    """
    Base class for content, that support writing directly to an image file
    """

    _result_file: Path = None

    @property
    def result_file(self) -> Path:
        if not self._result_file:
            self._result_file = get_temp_file(ext=f".{self.__class__.__name__}")
            with self._result_file.open("wb") as f:
                self.do_write(f)
        return self._result_file

    def write(self, file: io.BufferedIOBase):
        if self._result_file:
            with self.result_file.open("rb") as in_file:
                copy_sparse(file, in_file)
        else:
            self.do_write(file)

    @abc.abstractmethod
    def do_write(self, file: io.BufferedIOBase):
        pass
