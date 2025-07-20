import os
import sys
import unittest
from argparse import Namespace
from unittest.mock import patch

# Add the parent directory to sys.path to import the shared module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared import status


class TestStatus(unittest.TestCase):
    """Test class for status module."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = Namespace()  # Status doesn't use any command line args
        self.config = {"github_username": "testuser", "github_org": "testorg"}

    @patch("shared.status.get_clones")
    @patch("shared.status.cprint")
    def test_main_no_clones(self, mock_cprint, mock_get_clones):
        """Test main function when no clones exist."""
        # Setup mocks - no clones
        mock_get_clones.return_value = []

        # Run test
        status.main(self.args, self.config)

        # Verify header print
        mock_cprint.assert_called_once_with("\nSTATUS", status.colors.OKBLUE)

        # Verify get_clones was called
        mock_get_clones.assert_called_once_with(self.config)

    @patch("shared.status.get_clones")
    @patch("shared.status.get_branch_info")
    @patch("shared.status.get_index_info")
    @patch("shared.status.cprint")
    @patch("builtins.print")
    def test_main_all_on_default_branches(
        self,
        mock_print,
        mock_cprint,
        mock_get_index_info,
        mock_get_branch_info,
        mock_get_clones,
    ):
        """Test main function when all clones are on default branches."""
        # Setup mocks
        mock_clones = ["/path/to/repo1", "/path/to/repo2"]
        mock_get_clones.return_value = mock_clones

        # All repos on default branches (main and master)
        mock_get_branch_info.return_value = {
            "main": ["/path/to/repo1"],
            "master": ["/path/to/repo2"],
        }

        # All repos are clean
        mock_get_index_info.return_value = {"dirty": [], "clean": mock_clones}

        # Run test
        status.main(self.args, self.config)

        # Verify calls
        mock_get_clones.assert_called_once_with(self.config)
        mock_get_branch_info.assert_called_once_with(mock_clones)
        mock_get_index_info.assert_called_once_with(mock_clones)

        # Check for key print statements
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(
            any("Checking clone branch status" in call for call in print_calls)
        )
        self.assertTrue(
            any("Checking for uncomitted changes" in call for call in print_calls)
        )

        # Check cprint calls
        cprint_calls = [call for call in mock_cprint.call_args_list]
        self.assertTrue(
            any(
                "All clones are on the default branch" in str(call)
                for call in cprint_calls
            )
        )
        self.assertTrue(
            any("All clones are clean" in str(call) for call in cprint_calls)
        )

    @patch("shared.status.get_clones")
    @patch("shared.status.get_branch_info")
    @patch("shared.status.get_index_info")
    @patch("shared.status.cprint")
    def test_main_all_on_same_branch(
        self, mock_cprint, mock_get_index_info, mock_get_branch_info, mock_get_clones
    ):
        """Test main function when all clones are on the same feature branch."""
        # Setup mocks
        mock_clones = ["/path/to/repo1", "/path/to/repo2"]
        mock_get_clones.return_value = mock_clones

        # All repos on same feature branch
        mock_get_branch_info.return_value = {"feature-branch": mock_clones}

        # All repos are clean
        mock_get_index_info.return_value = {"dirty": [], "clean": mock_clones}

        with patch("builtins.print"):
            # Run test
            status.main(self.args, self.config)

        # Check cprint calls for same branch message
        cprint_calls = [call for call in mock_cprint.call_args_list]
        self.assertTrue(
            any(
                "All clones are on the feature-branch branch" in str(call)
                for call in cprint_calls
            )
        )

    @patch("shared.status.get_clones")
    @patch("shared.status.get_branch_info")
    @patch("shared.status.get_index_info")
    @patch("shared.status.cprint")
    @patch("shared.status.os.path.relpath")
    @patch("builtins.print")
    def test_main_different_branches(
        self,
        mock_print,
        mock_relpath,
        mock_cprint,
        mock_get_index_info,
        mock_get_branch_info,
        mock_get_clones,
    ):
        """Test main function when clones are on different branches."""
        # Setup mocks
        mock_clones = ["/path/to/repo1", "/path/to/repo2", "/path/to/repo3"]
        mock_get_clones.return_value = mock_clones
        mock_relpath.side_effect = lambda x: f"repos/{os.path.basename(x)}"

        # Repos on different branches
        mock_get_branch_info.return_value = {
            "main": ["/path/to/repo1"],
            "feature-branch": ["/path/to/repo2", "/path/to/repo3"],
        }

        # All repos are clean
        mock_get_index_info.return_value = {"dirty": [], "clean": mock_clones}

        # Run test
        status.main(self.args, self.config)

        # Check warning message
        cprint_calls = [call for call in mock_cprint.call_args_list]
        self.assertTrue(
            any(
                "WARNING: Clones are not all on the same branch" in str(call)
                for call in cprint_calls
            )
        )
        self.assertTrue(
            any("TIP: Run `./RepoLasso.py reset`" in str(call) for call in cprint_calls)
        )

        # Check that repo names are printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("repos/repo1" in call for call in print_calls))
        self.assertTrue(any("repos/repo2" in call for call in print_calls))

    @patch("shared.status.get_clones")
    @patch("shared.status.get_branch_info")
    @patch("shared.status.get_index_info")
    @patch("shared.status.cprint")
    @patch("shared.status.os.path.relpath")
    @patch("builtins.print")
    def test_main_with_dirty_repos(
        self,
        mock_print,
        mock_relpath,
        mock_cprint,
        mock_get_index_info,
        mock_get_branch_info,
        mock_get_clones,
    ):
        """Test main function when some clones have uncommitted changes."""
        # Setup mocks
        mock_clones = ["/path/to/repo1", "/path/to/repo2"]
        mock_get_clones.return_value = mock_clones
        mock_relpath.side_effect = lambda x: f"repos/{os.path.basename(x)}"

        # All on same branch
        mock_get_branch_info.return_value = {"main": mock_clones}

        # Some repos are dirty
        mock_get_index_info.return_value = {
            "dirty": ["/path/to/repo1"],
            "clean": ["/path/to/repo2"],
        }

        # Run test
        status.main(self.args, self.config)

        # Check warning message about uncommitted changes
        cprint_calls = [call for call in mock_cprint.call_args_list]
        self.assertTrue(
            any(
                "WARNING: Some clones have uncommitted changes" in str(call)
                for call in cprint_calls
            )
        )

        # Check that dirty repo is listed
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("repos/repo1" in call for call in print_calls))
        self.assertTrue(any("have uncommitted changes" in call for call in print_calls))

    @patch("shared.status.get_clones")
    @patch("shared.status.get_branch_info")
    @patch("shared.status.get_index_info")
    @patch("shared.status.cprint")
    def test_main_all_clean(
        self, mock_cprint, mock_get_index_info, mock_get_branch_info, mock_get_clones
    ):
        """Test main function when all clones are clean."""
        # Setup mocks
        mock_clones = ["/path/to/repo1", "/path/to/repo2"]
        mock_get_clones.return_value = mock_clones

        # All on same branch
        mock_get_branch_info.return_value = {"main": mock_clones}

        # All repos are clean
        mock_get_index_info.return_value = {"dirty": [], "clean": mock_clones}

        with patch("builtins.print"):
            # Run test
            status.main(self.args, self.config)

        # Check clean message
        cprint_calls = [call for call in mock_cprint.call_args_list]
        self.assertTrue(
            any("All clones are clean" in str(call) for call in cprint_calls)
        )


if __name__ == "__main__":
    unittest.main()
