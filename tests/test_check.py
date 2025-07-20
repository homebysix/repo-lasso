import os
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, mock_open, patch

# Add the parent directory to sys.path to import the shared module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared import check


class TestCheck(unittest.TestCase):
    """Test class for check module."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = Namespace(script="test_script.py", tries="3", revert=False)
        self.config = {"github_username": "testuser", "github_org": "testorg"}

    @patch("builtins.print")
    def test_summarize_no_errors(self, mock_print):
        """Test summarize with no failed checks."""
        results = {
            "repo1": {
                "file1.py": {"before": [0, 0, 0], "after": [0, 0, 0]},
                "file2.py": {"before": [0, 0, 0], "after": [0, 0, 0]},
            }
        }

        check.summarize(results)

        # Should print summary with 0 errors
        final_print_call = mock_print.call_args_list[-1]
        self.assertIn("0 files failed checks across 0 clones", str(final_print_call))

    @patch("shared.check.cprint")
    @patch("builtins.print")
    def test_summarize_with_errors(self, mock_print, mock_cprint):
        """Test summarize with failed checks."""
        results = {
            "repo1": {
                "file1.py": {"before": [0, 0, 0], "after": [1, 0, 0]},  # Error
                "file2.py": {"before": [0, 0, 0], "after": [0, 0, 0]},  # OK
            },
            "repo2": {
                "file3.py": {"before": [0, 0, 0], "after": [1, 1, 1]},  # Error
            },
        }

        check.summarize(results)

        # Should print repo names and file details
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("repo1" in call for call in print_calls))
        self.assertTrue(any("repo2" in call for call in print_calls))
        self.assertTrue(any("file1.py" in call for call in print_calls))
        self.assertTrue(any("file3.py" in call for call in print_calls))

        # Should print final summary
        final_print_call = mock_print.call_args_list[-1]
        self.assertIn("2 files failed checks across 2 clones", str(final_print_call))

        # Should call cprint for error details
        mock_cprint.assert_called()

    @patch("shared.check.cprint")
    @patch("shared.check.os.path.isfile")
    @patch("shared.check.sys.exit")
    def test_main_script_not_exists(self, mock_exit, mock_isfile, mock_cprint):
        """Test main function when script file doesn't exist."""
        mock_isfile.return_value = False

        check.main(self.args, self.config)

        mock_cprint.assert_any_call(
            "The check script does not exist: test_script.py", check.colors.FAIL
        )
        mock_exit.assert_called_once_with(1)

    @patch("shared.check.cprint")
    @patch("shared.check.os.path.isfile")
    @patch("shared.check.sys.exit")
    def test_main_invalid_tries_value(self, mock_exit, mock_isfile, mock_cprint):
        """Test main function with invalid tries value."""
        mock_isfile.return_value = True
        invalid_args = Namespace(script="test_script.py", tries="invalid", revert=False)

        check.main(invalid_args, self.config)

        mock_cprint.assert_any_call(
            "Number of tries must be an integer: test_script.py", check.colors.FAIL
        )
        mock_exit.assert_called_once_with(1)

    @patch("shared.check.summarize")
    @patch("shared.check.ThreadPool")
    @patch("shared.check.get_clones")
    @patch("shared.check.os.path.isdir")
    @patch("shared.check.os.path.isfile")
    @patch("shared.check.cprint")
    @patch("builtins.open", new_callable=mock_open)
    @patch("shared.check.json.dumps")
    def test_main_successful_execution(
        self,
        mock_json_dumps,
        mock_file_open,
        mock_cprint,
        mock_isfile,
        mock_isdir,
        mock_get_clones,
        mock_thread_pool,
        mock_summarize,
    ):
        """Test main function successful execution path."""
        # Setup mocks
        mock_isfile.return_value = True  # Script exists
        mock_isdir.return_value = True  # INTVDIR exists
        mock_get_clones.return_value = ["/path/to/repo1", "/path/to/repo2"]

        # Mock ThreadPool
        mock_pool = MagicMock()
        mock_pool.map.return_value = [
            {"repo1": {"file1.py": {"before": [0], "after": [0]}}},
            None,  # Some repos might return None
        ]
        mock_thread_pool.return_value.__enter__.return_value = mock_pool

        mock_json_dumps.return_value = '{"test": "data"}'

        check.main(self.args, self.config)

        # Verify key calls
        mock_cprint.assert_any_call("\nCHECK", check.colors.OKBLUE)
        mock_get_clones.assert_called_once_with(self.config)
        mock_json_dumps.assert_called_once()
        mock_summarize.assert_called_once()
        mock_file_open.assert_called_once()

    def test_parallelize_function(self):
        """Test the parallelize wrapper function."""
        mock_args = ("clone_path", self.args, 0, 1)

        with patch("shared.check.check_repo") as mock_check_repo:
            mock_check_repo.return_value = {"test": "result"}

            result = check.parallelize(mock_args)

            mock_check_repo.assert_called_once_with("clone_path", self.args, 0, 1)
            self.assertEqual(result, {"test": "result"})


if __name__ == "__main__":
    unittest.main()
