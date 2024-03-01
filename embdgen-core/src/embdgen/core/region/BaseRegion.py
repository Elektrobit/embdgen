# SPDX-License-Identifier: GPL-3.0-only

import abc
import io

from embdgen.core.utils.SizeType import SizeType
from embdgen.core.utils.class_factory import Config


@Config("name")
@Config("start", optional=True)
@Config("size", optional=True)
class BaseRegion(abc.ABC):
    """
    Base class for regions

    A region is not necessarily part of the partition table.
    It is just a part of the final image with a start and a size.
    """

    name: str
    """
    Name of the region
    """

    start: SizeType
    """
    Start of the region

    This can either be specified or should be calculated automatically
    by the label implementation.
    """

    size: SizeType
    """
    Size of the region

    This can either be specified or should be calculated automatically
    by the label or the content
    """

    def __init__(self) -> None:
        self.start = SizeType()
        self.size = SizeType()

    def __repr__(self) -> str:
        return f"{self.start.hex_bytes} - {(self.start + self.size).hex_bytes} Part {self.name}"

    def prepare(self) -> None:
        """
        Prepare for writing to the image file.

        Depending on the implementation, this calculates missing attributes (e.g. size)
        or even prepares a temporary file.
        """

    @abc.abstractmethod
    def write(self, out_file: io.BufferedIOBase):
        """
        Writes this region to the current position in ``out_file``
        """
