from pyads import AmsAddr
import unittest


class AdsTest(unittest.TestCase):

    def test_AmsAddr(self):
        netid = '5.33.160.54.1.1'
        port = 851

        adr = AmsAddr()
        self.assertEqual(adr.netid, '0.0.0.0.0.0')
        self.assertEqual(adr.port, 0)

        adr = AmsAddr(netid, port)
        self.assertEqual(adr.netid, netid)
        self.assertEqual(adr.port, port)


if __name__ == '__main__':
    unittest.main()
