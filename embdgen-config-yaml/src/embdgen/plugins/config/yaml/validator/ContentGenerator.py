# SPDX-License-Identifier: GPL-3.0-only

import strictyaml as y

from embdgen.core.content_generator import BaseContentGenerator, Factory

from .ObjectBase import ObjectBase
from ..ContentRegistry import ContentRegistry

class ContentGenerator(ObjectBase):
    RESULT_TYPE = BaseContentGenerator
    FACTORY = Factory

    def __call__(self, chunk) -> y.YAML:
        res = super().__call__(chunk)
        obj = res._value

        ContentRegistry.instance().register_all(obj.get_contents())

        return res
