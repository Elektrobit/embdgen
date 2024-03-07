# SPDX-License-Identifier: GPL-3.0-only

import re
from typing import List, Optional, Union
import pytest

from embdgen.core.utils.class_factory import FactoryBase, Config, Meta
from .plugintest import simple
from .plugintest.simple import BaseTestPlugin as SimpleBaseTestPlugin
from .plugintest.simple.TestPlugins import TestPlugin3 as SimpleTestPlugin3

from .plugintest import classkey
from .plugintest.classkey import BaseTestPlugin as ClassKeyBaseTestPlugin
from .plugintest.classkey.TestPlugins import *


@Config('foo')
class Base:
    foo: int
    """some doc"""

@Config('bar', doc="doc b")
class Child1(Base):
    bar: str
    """doc a"""

@Config('foo', optional=True)
@Config('foobar')
@Config('barfoo', "doc of barfoo")
class Child2(Base):
    foo: str

    @property
    def foobar(self) -> str:
        """a documented property"""
    @foobar.setter
    def foobar(self, value: str): pass

    @property
    def barfoo(self) -> int:
        """i-am-not-used"""
    @barfoo.setter
    def barfoo(self, value: int): pass

class TestConfig:
    def test_decorate(self):
        @Config('foo')
        @Config('bar', optional=True)
        @Config('foobar')
        @Config('barfoo')
        class FooBar():
            foo: int
            bar: str
            foobar: list

            @property
            def barfoo(self) -> int: pass
            @barfoo.setter
            def barfoo(self, value: int): pass

        assert len(Meta.get(FooBar)) == 4
        assert Meta.get(FooBar)['foo'] == Meta("foo", int, optional=False)
        assert Meta.get(FooBar)['bar'] == Meta("bar", str, optional=True)
        assert Meta.get(FooBar)['foobar'] == Meta("foobar", list, optional=False)
        assert Meta.get(FooBar)['barfoo'] == Meta("barfoo", int, optional=False)

    def test_inheritance(self):
        assert len(Meta.get(Base)) == 1
        assert Meta.get(Base)['foo'] == Meta("foo", int, "some doc", optional=False)

        assert len(Meta.get(Child1)) == 2
        assert Meta.get(Child1)['foo'] == Meta("foo", int, "some doc", optional=False)
        assert Meta.get(Child1)['bar'] == Meta("bar", str, "doc b", optional=False)

        assert len(Meta.get(Child2)) == 3
        assert Meta.get(Child2)['foo'] == Meta("foo", str, optional=True)
        assert Meta.get(Child2)['foobar'] == Meta("foobar", str, "a documented property")
        assert Meta.get(Child2)['barfoo'] == Meta("barfoo", int, "doc of barfoo")

    def test_missing_type(self):
        with pytest.raises(Exception, match="No type for member foo in class Test found"):
            @Config('foo')
            class Test: pass

    def test_broken_property(self):
        with pytest.raises(Exception, match="Property foo in class Test has different types for getter and setter"):
            @Config('foo')
            class Test:
                @property
                def foo(self) -> int: pass
                @foo.setter
                def foo(self, value: str): pass

        with pytest.raises(Exception, match="Property foo in class Test has no setter defined"):
            @Config('foo')
            class Test:
                @property
                def foo(self) -> int: pass

    def test_has_meta(self):
        class Foo: pass
        @Config('foo')
        class Bar:
            foo: str

        assert Meta.has_meta(Foo) is False
        assert Meta.has_meta(Bar) is True

class FactoryTestClass(FactoryBase):
    @classmethod
    def load(cls):
        return cls.load_plugins(simple, SimpleBaseTestPlugin, 'TEST_TYPE')

class FactoryTestClassWithClassKey(FactoryBase):
    ALLOW_SUBCLASS = True
    @classmethod
    def load(cls):
        return cls.load_plugins(classkey, ClassKeyBaseTestPlugin, 'TEST_CLASS_TYPE')

class TestFactorySimple():
    def setup_method(self):
        self.factory = FactoryTestClass()

    def test_types(self):
        assert self.factory.types() == ["plugin1", "plugin2", "plugin3", "plugin4", "plugin5"]

    def test_by_type(self):
        assert self.factory.by_type("plugin3") == SimpleTestPlugin3

class TestFactoryWithClassKey():
    def setup_method(self):
        self.factory = FactoryTestClassWithClassKey()

    def test_types(self):
        assert self.factory.types() == [str, List[int], CustomClass, CustomSubClass1, CustomSubClass2]
        assert self.factory.types(TestPlugin3) == [CustomClass, CustomSubClass1, CustomSubClass2]

    def test_by_type(self):
        assert self.factory.by_type(CustomSubClass1) == TestPlugin4
        assert self.factory.by_type(self.__class__) is None
        assert self.factory.by_type(Optional[CustomSubClass2]) == TestPlugin5
        assert self.factory.by_type(CustomSubClass3) == TestPlugin3, "Nonexisting type, but it's parent class is registered"
        with pytest.raises(Exception, match=re.escape("Unexpected type in <class 'tests.utils.test_class_factory.FactoryTestClassWithClassKey'>.by_type: typing.Union[str, int]")):
            self.factory.by_type(Union[str, int])
        assert self.factory.by_type("") is None
