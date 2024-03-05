# SPDX-License-Identifier: GPL-3.0-only

import abc
from typing import Type, Callable, Optional, Union, get_origin, get_args
import strictyaml as y

from embdgen.core.utils.class_factory import Meta
from .Factory import Factory, FactoryBase

class ObjectBase(y.Validator, abc.ABC):
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

    def __call__(self, chunk):
        pre_val = self.__base_schema(chunk)
        class_obj = self.__type_factory(pre_val['type'])
        validator = self.validator_from_type(class_obj, self.__base_schema)
        pre_val.revalidate(validator)
        obj = class_obj()
        self.set_attr_from_meta(obj, pre_val)

        v = y.YAML(chunk, validator=self)
        v._value = obj
        return v

    def get_validator(self, typecls: Type) -> Type[y.Validator]:
        TYPE_CLASS_MAP = {
            int: lambda: y.OrValidator(y.Int(), y.HexInt()),
            str: y.Str,
            bool: y.Bool
        }
        if get_origin(typecls) == Union:
            args = get_args(typecls)
            if len(args) == 2 and type(None) in args: # This is Optional[T]
                typecls = next(filter(lambda x: x is not type(None), args))
        validator = Factory.by_type(typecls)
        if validator:
            if issubclass(validator, ObjectBase):
                return lambda: validator.create(typecls) # type: ignore
            return validator
        if typecls in TYPE_CLASS_MAP:
            return TYPE_CLASS_MAP[typecls]
        raise Exception(f"cannot validate type {typecls}")

    def validator_from_type(self, type_class: Type, base_schema: y.Map):
        validator_map = base_schema._validator.copy() #pylint: disable = protected-access
        for name, value in Meta.get(type_class).items():
            if value.optional:
                name = y.Optional(name)
            validator = self.get_validator(value.typecls)
            validator_map[name] = validator()

        return y.Map(validator_map)

    def set_attr_from_meta(self, instance: object, conf: y.YAML):
        for name in Meta.get(instance).keys():
            if name in conf:
                setattr(instance, name, conf[name].value)
