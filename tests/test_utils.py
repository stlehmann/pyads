from unittest import TestCase

from pyads.utils import deprecated, find_wstring_null_terminator


class UtilsTestCase(TestCase):
    def test_deprecated_decorator(self):
        @deprecated()
        def deprecated_fct():
            pass

        with self.assertWarns(DeprecationWarning):
            deprecated_fct()

    def test_find_wstring_null_terminator(self):
        data = "hello world".encode("utf-16-le")
        self.assertEqual(None, find_wstring_null_terminator(data))
        data = "hello world".encode("utf-16-le") + b"\x00\x00"
        self.assertEqual(22, find_wstring_null_terminator(data))
