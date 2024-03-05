# SPDX-License-Identifier: GPL-3.0-only

from typing import Dict, Type

from embdgen.plugins import label

from ..utils.class_factory import FactoryBase
from .BaseLabel import BaseLabel

class Factory(FactoryBase[BaseLabel]):
    """
    Factory class for label classes
    """

    @classmethod
    def load(cls) -> Dict[str, Type[BaseLabel]]:
        return cls.load_plugins(label, BaseLabel, 'LABEL_TYPE')
