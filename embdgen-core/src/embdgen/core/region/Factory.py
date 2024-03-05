# SPDX-License-Identifier: GPL-3.0-only

from typing import Dict, Type

from embdgen.plugins import region

from ..utils.class_factory import FactoryBase
from .BaseRegion import BaseRegion

class Factory(FactoryBase[BaseRegion]):
    @classmethod
    def load(cls) -> Dict[str, Type[BaseRegion]]:
        return cls.load_plugins(region, BaseRegion, 'PART_TYPE')
