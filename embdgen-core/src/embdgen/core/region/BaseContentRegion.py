# SPDX-License-Identifier: GPL-3.0-only

from embdgen.core.region import BaseRegion  # type: ignore
from embdgen.core.utils.SizeType import SizeType  # type: ignore
from embdgen.core.content import BaseContent  # type: ignore
from embdgen.core.utils.class_factory import Config  # type: ignore


@Config("content")
class BaseContentRegion(BaseRegion):
    content: BaseContent = None
    size: SizeType

    def prepare(self) -> None:
        if not self.size.is_undefined:
            self.content.size = self.size
        self.content.prepare()

        if self.size.is_undefined:
            self.size = self.content.size

        super().prepare()

    def __repr__(self) -> str:
        return f"{self.start.hex_bytes} - {(self.start + self.size).hex_bytes} Part {self.name}\n    {self.content}"
