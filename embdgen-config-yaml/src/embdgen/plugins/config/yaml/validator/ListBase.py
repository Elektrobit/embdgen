# SPDX-License-Identifier: GPL-3.0-only

import strictyaml as y
class ListBase(y.Seq):
    def __call__(self, chunk) -> y.YAML:
        self.validate(chunk)
        v = y.YAML(chunk, validator=self)
        v._value = list(map(lambda x: x.value, v.value))
        return v
