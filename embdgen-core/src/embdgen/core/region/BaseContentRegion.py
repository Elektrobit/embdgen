# SPDX-License-Identifier: GPL-3.0-only

import abc

from embdgen.core.region import BaseRegion
from embdgen.core.content import BaseContent
from embdgen.core.utils.class_factory import Config


@Config("content")
class BaseContentRegion(BaseRegion, abc.ABC):
    content: BaseContent = None

    def prepare(self) -> None:
        if not self.size.is_undefined:
            self.content.size = self.size
        self.content.prepare()

        if self.size.is_undefined:
            self.size = self.content.size

        super().prepare()

    def __repr__(self) -> str:
        return f"{self.start.hex_bytes} - {(self.start + self.size).hex_bytes} Part {self.name}\n    {self.content}"
