"""
:author: Stefan Lehmann <stefan.st.lehmann@gmail.com>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on 2017-10-14 18:17:53
:last modified by:   Stefan Lehmann
:last modified time: 2017-10-14 18:36:03

"""
import unittest
from datetime import datetime, timedelta, timezone
from pyads.filetimes import dt_to_filetime, filetime_to_dt


class FiletimesTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_filetime_dt_conversion(self):

        some_timezone = timezone(timedelta(hours=3), name="Ankara")
        # Ankara (Turkey) has UTC+3 ("EEST")

        dts = [
            # Already in UTC:
            datetime(2017, 10, 13, 10, 11, 12, tzinfo=timezone.utc),

            # Different timezone:
            datetime(2017, 10, 13, 13, 11, 12, tzinfo=some_timezone),

            # No timezone at all:
            datetime(2017, 10, 13, 10, 11, 12),
        ]

        for dt in dts:
            ft = dt_to_filetime(dt)
            dt_back = filetime_to_dt(ft)

            # should be identical
            if dt.tzinfo is None:
                dt_back = dt_back.replace(tzinfo=None)
            self.assertEqual(dt, dt_back)


if __name__ == "__main__":
    unittest.main()
