# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
from embdgen.core.label import BaseLabel
import strictyaml as y

from embdgen.core.config.BaseConfig import BaseConfig
from embdgen.core.label.BaseLabel import BaseLabel

from embdgen.plugins.config.yaml.validator.Label import Label as LabelValidator
from embdgen.plugins.config.yaml.validator.ContentGenerator import ContentGenerator as ContentGeneratorValidator
from embdgen.plugins.config.yaml.ContentRegistry import ContentRegistry

__version__ = "0.0.1"

class YAML(BaseConfig):
    CONFIG_TYPE = "yaml"

    def _get_schema(self) -> y.OrValidator:
        return y.OrValidator(
            LabelValidator(),
            y.Map(
                {
                    y.Optional("contents"): y.Seq(ContentGeneratorValidator()),
                    "image": LabelValidator(),
                }
            ),
        )

    def _get_label(self, cfg) -> BaseLabel:
        return cfg["image"].value if cfg.is_mapping() and "image" in cfg else cfg.value

    @classmethod
    def probe(cls, filename: Path) -> bool:
        try:
            with filename.open("r", encoding="utf-8") as f:
                res = y.load(f.read())
                return not isinstance(res.value, (str, int))
        except (UnicodeDecodeError, y.YAMLError):
            return False

    def load(self, filename: Path) -> BaseLabel:
        ContentRegistry.instance().clear()
        with filename.open(encoding="utf-8") as f:
            return self._get_label(y.load(f.read(), self._get_schema()))

    def load_str(self, data: str) -> BaseLabel:
        ContentRegistry.instance().clear()
        return self._get_label(y.load(data, self._get_schema()))
