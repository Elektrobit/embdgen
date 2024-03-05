# SPDX-License-Identifier: GPL-3.0-only

from typing import Dict, Type

from embdgen.plugins import content

from embdgen.core.utils.class_factory import FactoryBase
from .BaseContent import BaseContent

class Factory(FactoryBase[BaseContent]):
    """
    Factory class for content
    """

    @classmethod
    def load(cls) -> Dict[str, Type[BaseContent]]:
        return cls.load_plugins(content, BaseContent, 'CONTENT_TYPE')
