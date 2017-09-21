import unittest

from pyads.testserver_ex import structs


class TestserverExTestCase(unittest.TestCase):
    
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_amstcpheader(self):

        # test for empty data
        x = structs.AmsTcpHeader()
        self.assertEqual(b'\x00' * 6, x.data)
        self.assertEqual(0, x.length)

        # check for correct unpacking
        x = structs.AmsTcpHeader(b'\x00\x00\x1f\x00\x00\x00')
        self.assertEqual(31, x.length)

        # check for correct packing
        x.length = 255
        self.assertEqual(b'\x00\x00\xff\x00\x00\x00', x.data)


if __name__ == '__main__':
    unittest.main()
