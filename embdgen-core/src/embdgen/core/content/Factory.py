# SPDX-License-Identifier: GPL-3.0-only

from typing import Any

from embdgen.plugins import content
from embdgen.core.utils.class_factory import FactoryBase
from embdgen.core.content.BaseContent import BaseContent


class Factory(FactoryBase[BaseContent]):
    """
    Factory class for content
    """

    @classmethod
    def load(cls):
        return cls.load_plugins(content, BaseContent, 'CONTENT_TYPE')
