# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
from embdgen.core.config.BaseConfig import BaseConfig
from embdgen.core.label.BaseLabel import BaseLabel

class ConfigFoo(BaseConfig):
    def load(self, filename: Path) -> BaseLabel:
        return None

    def load_str(self, data: str) -> BaseLabel:
        return None

def test_BaseConfig():
    c = ConfigFoo()
    assert c.probe(Path("")) is False
