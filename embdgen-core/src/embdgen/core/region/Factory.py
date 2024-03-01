# SPDX-License-Identifier: GPL-3.0-only

from typing import Any
from embdgen.plugins import region
from embdgen.core.utils.class_factory import FactoryBase
from embdgen.core.region import BaseRegion


class Factory(FactoryBase[BaseRegion]):
    @classmethod
    def load(cls):
        return cls.load_plugins(region, BaseRegion, 'PART_TYPE')
