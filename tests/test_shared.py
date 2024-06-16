import argparse
import os
import unittest

from shared import colors, get_config, readable_time, trim_leading_org

TESTDIR = os.path.dirname(__file__)


class TestShared(unittest.TestCase):
    """Test class for shared modules."""

    test_args = argparse.Namespace(
        gh_user="nobody",
        gh_org="macadmins",
        gh_token="E391119E-7A54-4F72-8083-332FF1388516".replace("-", "").lower(),
        exclude_repo=[],
    )

    def test_colors(self):
        """test colors class"""
        clrs = (
            colors.HEADER,
            colors.OKBLUE,
            colors.OKGREEN,
            colors.WARNING,
            colors.FAIL,
            colors.ENDC,
        )
        for clr in clrs:
            self.assertTrue(clr.startswith("\033["))
            self.assertTrue(clr.endswith("m"))

    def test_get_config(self):
        """get_config gets configuration"""
        result = get_config(os.path.join(TESTDIR, "test_config.json"), self.test_args)
        expected = {
            "github_username": "nobody",
            "github_org": "macadmins",
            "github_token": "e391119e7a544f728083332ff1388516",
        }
        self.assertEqual(result, expected)

    def test_readable_time(self):
        """readable_time produces readable time from an integer of seconds"""
        result = readable_time(0)
        self.assertEqual(result, "0 seconds")
        result = readable_time(1)
        self.assertEqual(result, "1 second")
        result = readable_time(59)
        self.assertEqual(result, "59 seconds")
        result = readable_time(3661)
        self.assertEqual(result, "1 hour, 1 minute, 1 second")
        result = readable_time(208640)
        self.assertEqual(result, "2 days, 9 hours, 57 minutes, 20 seconds")

    def test_trim_leading_org_trims(self):
        """trim_leading_org trims leading org"""
        result = trim_leading_org("autopkg/recipes", "autopkg")
        self.assertEqual(result, "recipes")

    def test_trim_leading_org_preserves(self):
        """trim_leading_org preserves input if no leading org"""
        result = trim_leading_org("foo", "bar")
        self.assertEqual(result, "foo")
