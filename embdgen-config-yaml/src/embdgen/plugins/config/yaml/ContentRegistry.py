from typing import Optional, Dict

from embdgen.core.content.BaseContent import BaseContent

class ContentRegistry:
    __instance: Optional["ContentRegistry"] = None
    _registry: Dict[str, BaseContent]


    @classmethod
    def instance(cls) -> "ContentRegistry":
        if not cls.__instance:
            cls.__instance = ContentRegistry()
        return cls.__instance

    def __init__(self) -> None:
        self._registry = {}

    def clear(self) -> None:
        self._registry = {}

    def register_all(self, contents: Dict[str, BaseContent]) -> None:
        for key, content in contents.items():
            if key in self._registry:
                raise Exception(f"Duplicate key {key} in contents")
            self._registry[key] = content

    def find(self, key: str) -> BaseContent:
        return self._registry[key]
