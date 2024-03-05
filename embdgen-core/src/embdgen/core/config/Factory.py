# SPDX-License-Identifier: GPL-3.0-only

from typing import Dict, Type

from embdgen.plugins import config

from ..utils.class_factory import FactoryBase
from .BaseConfig import BaseConfig

class Factory(FactoryBase[BaseConfig]):
    @classmethod
    def load(cls)-> Dict[str, Type[BaseConfig]]:
        return cls.load_plugins(config, BaseConfig, 'CONFIG_TYPE')
