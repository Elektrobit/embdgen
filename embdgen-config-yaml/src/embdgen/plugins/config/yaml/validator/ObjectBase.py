# SPDX-License-Identifier: GPL-3.0-only

import abc
from inspect import isclass
from typing import Type, Callable, Optional, Union, get_origin, get_args

import strictyaml as y

from embdgen.core.content import BaseContent
from embdgen.plugins.config.yaml.validator.ListBase import ListBase
from embdgen.core.utils.class_factory import Meta
from .Factory import Factory, FactoryBase

class BaseObjectBase(y.Validator):
    def validator_from_type(self, type_class: Type, base_schema: y.Map) -> y.Map:
        validator_map = base_schema._validator.copy() #pylint: disable = protected-access
        for name, value in Meta.get(type_class).items():
            if value.optional:
                name = y.Optional(name)
            validator = self.get_validator(value.typecls)
            validator_map[name] = validator()

        return y.Map(validator_map)

    def set_attr_from_meta(self, instance: object, conf: y.YAML) -> None:
        for name, meta in Meta.get(instance).items():
            if name in conf:
                value = conf[name].value
                if (isclass(meta.typecls) and
                    issubclass(meta.typecls, BaseContent) and
                    not isinstance(value, meta.typecls)):
                    raise Exception(f"Invalid type for attribute {name}, expected {meta.typecls}, got {type(value)}")
                setattr(instance, name, value)

    def object_from_meta(self, typecls: Type) -> Optional[Callable[[], y.Validator]]:
        is_list = get_origin(typecls) is list
        if is_list:
            typecls = get_args(typecls)[0]
        if isclass(typecls) and Meta.has_meta(typecls):
            if is_list:
                return lambda: ListBase(SimpleMetaObject(typecls))
            return lambda: SimpleMetaObject(typecls)
        return None

    def get_validator(self, typecls: Type) -> Callable[[], y.Validator]:
        TYPE_CLASS_MAP = {
            int: lambda: y.OrValidator(y.Int(), y.HexInt()),
            str: y.Str,
            bool: y.Bool
        }
        internal_type = typecls
        if get_origin(internal_type) == Union:
            args = get_args(internal_type)
            if len(args) == 2 and type(None) in args: # This is Optional[T]
                internal_type = next(filter(lambda x: x is not type(None), args))
        validator = Factory.by_type(internal_type)
        if validator is not None:
            if issubclass(validator, ObjectBase):
                return lambda: validator.create(typecls) # type: ignore[union-attr]
            return validator
        if internal_type in TYPE_CLASS_MAP:
            return TYPE_CLASS_MAP[internal_type]
        obj_validator = self.object_from_meta(internal_type)
        if obj_validator is not None:
            return obj_validator
        raise Exception(f"cannot validate type {typecls}")

class SimpleMetaObject(BaseObjectBase):
    """
    Validator wrapper for an object with metadata,
    that is not polymorphic
    """
    def __init__(self, class_obj: Type) -> None:
        self.class_obj = class_obj

    def __call__(self, chunk) -> y.YAML:
        validator = self.validator_from_type(self.class_obj, y.Map({}))
        result = validator(chunk)
        obj = self.class_obj()
        self.set_attr_from_meta(obj, result)

        v = y.YAML(chunk, validator=self)
        v._value = obj
        return v

class ObjectBase(BaseObjectBase, abc.ABC):
    """
    Validator wrapper for a polymorphic object,
    where the actual implementation is defined by the "type" property
    """
    __base_schema: y.Validator
    __type_factory: Callable

    FACTORY: Type[FactoryBase]

    @classmethod
    def create(cls, expected_class: Type):
        return cls(expected_class)

    def __init__(self, expected_class: Optional[Type] = None) -> None:
        self.__type_factory = self.FACTORY.by_type
        self.__base_schema = y.MapCombined({
            'type': y.Enum(self.FACTORY.types(expected_class))
        }, y.Str(), y.Any())

    def __call__(self, chunk) -> y.YAML:
        pre_val = self.__base_schema(chunk)
        class_obj = self.__type_factory(pre_val['type'])
        validator = self.validator_from_type(class_obj, self.__base_schema)
        pre_val.revalidate(validator)
        obj = class_obj()
        self.set_attr_from_meta(obj, pre_val)

        v = y.YAML(chunk, validator=self)
        v._value = obj
        return v
