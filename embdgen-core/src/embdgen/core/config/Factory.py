# SPDX-License-Identifier: GPL-3.0-only

from typing import Any
from embdgen.plugins import config
from embdgen.core.utils.class_factory import FactoryBase
from embdgen.core.config.BaseConfig import BaseConfig


class Factory(FactoryBase[BaseConfig]):
    @classmethod
    def load(cls) -> dict[Any, Any]:
        return cls.load_plugins(config, BaseConfig, "CONFIG_TYPE")
