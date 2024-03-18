# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
from abc import ABC, abstractmethod

from embdgen.core.label import BaseLabel


class BaseConfig(ABC):
    @classmethod
    def probe(cls, _filename: Path) -> bool:
        return False

    @abstractmethod
    def load(self, filename: Path) -> BaseLabel:
        """
        Load configuration from a filename
        """

    @abstractmethod
    def load_str(self, data: str) -> BaseLabel:
        """
        Load configuration from configuration string source
        """
