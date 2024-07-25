# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import strictyaml as y

from embdgen.core.config.BaseConfig import BaseConfig
from embdgen.core.label.BaseLabel import BaseLabel

from embdgen.plugins.config.yaml.validator.Label import Label as LabelValidator
from embdgen.plugins.config.yaml.validator.ContentGenerator import ContentGenerator as ContentGeneratorValidator
from embdgen.plugins.config.yaml.ContentRegistry import ContentRegistry

__version__ = "0.1.1"

class YAML(BaseConfig):
    CONFIG_TYPE = "yaml"

    @classmethod
    def probe(cls, filename: Path) -> bool:
        try:
            with filename.open("r", encoding="utf-8") as f:
                res = y.load(f.read())
                return not isinstance(res.value, (str, int))
        except (UnicodeDecodeError, y.YAMLError):
            return False

    def load(self, filename: Path) -> BaseLabel:
        with filename.open(encoding="utf-8") as f:
            return self.load_str(f.read())

    def load_str(self, data: str) -> BaseLabel:
        root_schema = y.OrValidator(
            LabelValidator(),
            y.Map({
                y.Optional("contents"): y.Seq(ContentGeneratorValidator()),
                "image": LabelValidator()
            })
        )

        ContentRegistry.instance().clear()
        conf = y.load(data, root_schema)

        if conf.is_mapping() and "image" in conf:
            label = conf["image"].value
        else:
            label = conf.value

        return label
