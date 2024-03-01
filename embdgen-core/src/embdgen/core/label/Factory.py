# SPDX-License-Identifier: GPL-3.0-only

from typing import Any
from embdgen.plugins import label
from embdgen.core.utils.class_factory import FactoryBase
from embdgen.core.label.BaseLabel import BaseLabel


class Factory(FactoryBase[BaseLabel]):
    """
    Factory class for label classes
    """

    @classmethod
    def load(cls) -> dict[Any, Any]:
        return cls.load_plugins(label, BaseLabel, "LABEL_TYPE")
