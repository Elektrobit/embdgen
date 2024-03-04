# SPDX-License-Identifier: GPL-3.0-only

import abc
from typing import Dict
from embdgen.core.content.BaseContent import BaseContent
from embdgen.core.utils.class_factory import Config


@Config("name")
class BaseContentGenerator (abc.ABC):
    name: str
    """Name of this content generator"""

    @abc.abstractmethod
    def get_contents(self) -> Dict[str, BaseContent]:
        pass
