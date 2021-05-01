# test_foo.py

import unittest
from src.foo import Foo


class TestFoo(unittest.TestCase):
    def setUp(self) -> None:
        self.foo = Foo(name='test')

    def test_init(self):
        self.assertEqual('test', self.foo.name)