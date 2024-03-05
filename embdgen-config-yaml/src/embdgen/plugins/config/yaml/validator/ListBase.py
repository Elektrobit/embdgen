# SPDX-License-Identifier: GPL-3.0-only

import abc
import strictyaml as y # type: ignore

class ListBase(y.Seq, abc.ABC):
    def __call__(self, chunk):
        self.validate(chunk)
        v = y.YAML(chunk, validator=self)
        v._value = list(map(lambda x: x.value, v.value))
        return v
