import os
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared import report


class TestReport(unittest.TestCase):
    """Test class for report module."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = Namespace()
        self.config = {"github_username": "testuser", "github_org": "testorg"}

    @patch("shared.report.cprint")
    @patch("shared.report.os.path.isdir")
    @patch("shared.report.os.listdir")
    @patch("shared.report.os.makedirs")
    def test_main_no_initiatives_early_return(
        self, mock_makedirs, mock_listdir, mock_isdir, mock_cprint
    ):
        """Test report when no initiatives exist - should return early."""
        # Setup mocks - initiatives directory exists but is empty
        mock_isdir.return_value = True
        mock_listdir.return_value = []  # Empty directory

        # Run test
        result = report.main(self.args, self.config)

        # Should return None (early return)
        self.assertIsNone(result)

        # Should have called cprint with warning about no initiatives
        mock_cprint.assert_called()
        warning_found = any(
            "No initiatives found" in str(call) for call in mock_cprint.call_args_list
        )
        self.assertTrue(warning_found)

    @patch("builtins.print")  # Mock the "Found X initiatives" print
    @patch("shared.report.cprint")
    @patch("shared.report.get_org_repos")
    @patch("shared.report.os.path.isdir")
    @patch("shared.report.os.listdir")
    @patch("shared.report.os.path.isfile")
    @patch("shared.report.os.makedirs")
    @patch("builtins.open")
    @patch("json.dumps")
    def test_main_with_initiatives(
        self,
        mock_dumps,
        mock_open,
        mock_makedirs,
        mock_isfile,
        mock_listdir,
        mock_isdir,
        mock_get_repos,
        mock_cprint,
        mock_print,
    ):
        """Test report with initiatives - basic flow."""
        # Setup mocks
        mock_isdir.return_value = True
        mock_listdir.return_value = ["test-initiative.md"]
        mock_isfile.return_value = False  # No existing report file
        mock_dumps.return_value = "{}"

        # Mock repository with no PRs
        mock_repo = MagicMock()
        mock_repo.full_name = "testorg/testrepo"
        mock_repo.get_pulls.return_value = []
        mock_get_repos.return_value = [mock_repo]

        # Run test
        report.main(self.args, self.config)

        # Verify key interactions
        mock_get_repos.assert_called_once_with(self.config, self.args)
        mock_repo.get_pulls.assert_called_once()

        # Should have printed found initiatives message
        found_print = any(
            "Found 1 initiatives" in str(call) for call in mock_print.call_args_list
        )
        self.assertTrue(found_print)


if __name__ == "__main__":
    unittest.main()
