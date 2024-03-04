# SPDX-License-Identifier: GPL-3.0-only

import strictyaml as y

from embdgen.plugins.config.yaml.ContentRegistry import ContentRegistry
from embdgen.core.content import BaseContent, Factory

from .ObjectBase import ObjectBase

class Content(ObjectBase):
    RESULT_TYPE = BaseContent
    FACTORY = Factory

    def __call__(self, chunk) -> y.YAML:
        if chunk.is_scalar():
            result = y.Str()(chunk)
            result._value = ContentRegistry.instance().find(result.value)
            return result
        return super().__call__(chunk)
