from unittest import TestCase

from pyads.utils import deprecated


class UtilsTestCase(TestCase):
    def test_deprecated_decorator(self):
        @deprecated()
        def deprecated_fct():
            pass

        with self.assertWarns(DeprecationWarning):
            deprecated_fct()
