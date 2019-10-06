"""
:author: Stefan Lehmann <stefan.st.lehmann@gmail.com>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on 2017-10-14 18:17:53
:last modified by:   Stefan Lehmann
:last modified time: 2017-10-14 18:36:03

"""
import unittest
from datetime import datetime, timedelta
from pyads.filetimes import UTC, dt_to_filetime, filetime_to_dt


class FiletimesTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_utc_class(self):

        utc = UTC()

        # utc should have no offset to utc time
        self.assertEqual(timedelta(0), utc.utcoffset(datetime.now()))

        # timezone is UTC
        self.assertEqual("UTC", utc.tzname(datetime.now()))

        # daylight savings time is 0
        self.assertEqual(timedelta(0), utc.dst(datetime.now()))

    def test_filetime_dt_conversion(self):

        dt_now = datetime(2017, 10, 13, 10, 11, 12)

        ft = dt_to_filetime(dt_now)
        dt = filetime_to_dt(ft)

        # should be identical
        self.assertEqual(dt_now, dt)


if __name__ == "__main__":
    unittest.main()
