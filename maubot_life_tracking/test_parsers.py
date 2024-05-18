import unittest
from maubot_life_tracking.parsers import parse_datetime, parse_interval, render_template
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


ZONE = ZoneInfo("America/Los_Angeles")


class TestParsers(unittest.TestCase):
    def test_parse_datetime_today(self) -> None:
        now = datetime.now(ZONE)
        result = parse_datetime("today 15:05", ZONE)
        self.assertEqual(result.day, now.day)
        self.assertEqual(result.month, now.month)
        self.assertEqual(result.year, now.year)
        self.assertEqual(result.hour, 15)
        self.assertEqual(result.minute, 5)
        self.assertEqual(result.tzinfo, ZONE)
    
    def test_parse_datetime_tomorrow(self) -> None:
        tom = datetime.now(ZONE) + timedelta(days=1)
        result = parse_datetime("tomorrow 15:05", ZONE)
        self.assertEqual(result.day, tom.day)
        self.assertEqual(result.month, tom.month)
        self.assertEqual(result.year, tom.year)
        self.assertEqual(result.hour, 15)
        self.assertEqual(result.minute, 5)
        self.assertEqual(result.tzinfo, ZONE)
    
    def test_parse_datetime(self) -> None:
        result = parse_datetime("2005-11-22 09:00", ZONE)
        self.assertEqual(result.day, 22)
        self.assertEqual(result.month, 11)
        self.assertEqual(result.year, 2005)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, ZONE)
    
    def test_parse_interval(self) -> None:
        self.assertEqual(parse_interval("15d"), timedelta(days=15))
        self.assertEqual(parse_interval("15h"), timedelta(hours=15))
        self.assertEqual(parse_interval("15m"), timedelta(minutes=15))
        self.assertEqual(parse_interval("15s"), timedelta(seconds=15))
    
    def test_render_template(self) -> None:
        now = datetime(2024, 5, 17)
        self.assertEqual("it is Friday, May 17, 2024 - hi!", render_template("it is $(date) - hi!", now))


if __name__ == "__main__":
    unittest.main()
