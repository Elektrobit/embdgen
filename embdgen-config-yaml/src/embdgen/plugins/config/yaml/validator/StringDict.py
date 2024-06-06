# SPDX-License-Identifier: GPL-3.0-only

from typing import Dict
import strictyaml as y
from  strictyaml.parser import YAMLChunk

class StringDict(y.MapPattern):
    RESULT_TYPE = Dict[str, str]

    def __init__(self):
        super().__init__(y.Str(), y.Str())

    def __call__(self, chunk: YAMLChunk) -> y.YAML:
        self.validate(chunk)
        v = y.YAML(chunk, validator=self)
        v._value = {k._value: v._value for k, v in v._value.items()}
        return v
