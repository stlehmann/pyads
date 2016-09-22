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

        # check if ams addr struct has been changed
        ams_addr_numbers = [x for x in adr._ams_addr.netId.b]
        netid_numbers = [int(x) for x in netid.split('.')]
        self.assertEqual(len(ams_addr_numbers), len(netid_numbers))
        for i in range(len(ams_addr_numbers)):
            self.assertEqual(ams_addr_numbers[i], netid_numbers[i])
        self.assertEqual(adr.port, adr._ams_addr.port)


if __name__ == '__main__':
    unittest.main()
