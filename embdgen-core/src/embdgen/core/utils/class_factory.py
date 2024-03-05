# SPDX-License-Identifier: GPL-3.0-only

import abc
from typing import Any, List, Type, Dict, Optional, Union, get_origin, get_args, Generic, TypeVar, get_type_hints
from inspect import isclass, signature
from pkgutil import iter_modules
from importlib import import_module
from types import ModuleType
from dataclasses import dataclass

@dataclass
class Meta():
    """
    Object meta information for factory classes
    """
    _META_KEY = "__embdgen_meta__"

    name: str
    typecls: Type
    doc: str = ""
    optional: bool = False

    @classmethod
    def get(cls, obj: object) -> Dict[str, 'Meta']:
        return getattr(obj, cls._META_KEY, {})

    @classmethod
    def set(cls, obj: Type, value: 'Meta') -> None:
        name = value.name
        attr = cls.get(obj)
        if cls._META_KEY not in obj.__dict__: # Test if the attribute is defined on the instance, not the parents
            if hasattr(obj, cls._META_KEY):
                attr = getattr(obj, cls._META_KEY).copy() # Use the parent's meta as preset
            setattr(obj, cls._META_KEY, attr)
        attr[name] = value

def try_read_doc(cls: Type, name: str) -> str:
    try:
        from sphinx.pycode import ModuleAnalyzer # pylint: disable=import-outside-toplevel
    except ModuleNotFoundError: # pragma: no cover
        return ""
    analyzer = ModuleAnalyzer.for_module(cls.__module__)
    analyzer.analyze()
    return "\n".join(analyzer.find_attr_docs().get((cls.__name__, name), [])).strip()

CT = TypeVar("CT")

def Config(name: str, doc="", optional=False):
    """
    Metadata decorator for classes for the BaseFactory
    """
    def decorate(cls: Type[CT]) -> Type[CT]:
        local_doc = doc
        name_prop = getattr(cls, name, None)
        if name_prop is not None and isinstance(name_prop, property):
            if name_prop.fset is None:
                raise Exception(f"Property {name} in class {cls.__name__} has no setter defined")
            setter_type = list(signature(name_prop.fset).parameters.values())[1].annotation
            getter_type = signature(name_prop.fget).return_annotation
            if getter_type != setter_type:
                raise Exception(f"Property {name} in class {cls.__name__} has different types for getter and setter")
            if not local_doc:
                local_doc = name_prop.fget.__doc__ or ""
            hints = {name: getter_type}
        else:
            hints = get_type_hints(cls)

        if name not in hints:
            raise Exception(f"No type for member {name} in class {cls.__name__} found")

        if not local_doc:
            local_doc = try_read_doc(cls, name)

        meta = Meta(name, hints[name], local_doc, optional)
        Meta.set(cls, meta)
        return cls
    return decorate


T = TypeVar("T")
class FactoryBase(abc.ABC, Generic[T]):
    __class_map = None
    ALLOW_SUBCLASS = False

    @classmethod
    @abc.abstractmethod
    def load(cls) -> dict:
        pass

    @classmethod
    def load_plugins(cls, root_module: ModuleType, baseclass: Type[T], key: str) -> Dict[Any, Type[T]]:
        retval = {}
        for (_, module_name, _) in iter_modules(list(root_module.__path__)):
            module = import_module(f"{root_module.__name__}.{module_name}")
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if isclass(attribute) and issubclass(attribute, baseclass) and hasattr(attribute, key):
                    retval[getattr(attribute, key)] = attribute
        return retval

    @classmethod
    def class_map(cls) -> Dict[Any, Type[T]]:
        if cls.__class_map is None:
            cls.__class_map = cls.load()
        return cls.__class_map

    @classmethod
    def by_type(cls, type_any: Any) -> Optional[Type[T]]:
        if get_origin(type_any) == Union:
            args = get_args(type_any)
            if len(args) == 2 and type(None) in args: # This is Optional[T]
                type_any = next(filter(lambda x: x is not type(None), args))
            else:
                raise Exception(f"Unexpected type in {cls}.by_type: {type_any}")
        impl_class = cls.class_map().get(type_any, None)
        if impl_class or not cls.ALLOW_SUBCLASS:
            return impl_class

        for cur_type_class, impl_class in cls.class_map().items():
            if get_origin(cur_type_class) == list:
                continue
            if issubclass(type_any, cur_type_class):
                return impl_class
        return None


    @classmethod
    def types(cls, parent_class: Optional[Type] = None) -> List[Any]:
        if not parent_class:
            return list(cls.class_map().keys())

        out = []
        for cur_type_class, impl_class in cls.class_map().items():
            if get_origin(cur_type_class) == list:
                continue
            if issubclass(impl_class, parent_class):
                out.append(cur_type_class)
        return out
