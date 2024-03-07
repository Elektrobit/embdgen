# SPDX-License-Identifier: GPL-3.0-only

from embdgen.plugins import content_generator

from ..utils.class_factory import FactoryBase
from .BaseContentGenerator import BaseContentGenerator

class Factory(FactoryBase[BaseContentGenerator]):
    """
    Factory class for content
    """

    @classmethod
    def load(cls):
        return cls.load_plugins(content_generator, BaseContentGenerator, 'CONTENT_TYPE')
