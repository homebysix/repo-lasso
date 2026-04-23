import os
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared import branch


class TestBranch(unittest.TestCase):
    """Test class for branch module."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = Namespace(name="test-branch")
        self.config = {"github_username": "testuser", "github_org": "testorg"}

    @patch("shared.branch.cprint")
    @patch("shared.branch.get_clones")
    @patch("shared.branch.get_branch_info")
    @patch("shared.branch.get_index_info")
    @patch("shared.branch.create_branch")
    def test_main_create_new_branch_from_default(
        self,
        mock_create_branch,
        mock_get_index_info,
        mock_get_branch_info,
        mock_get_clones,
        mock_cprint,
    ):
        """Test creating new branch from default branch (main/master)."""
        # Setup mocks - all clones on default branch
        mock_clones = ["/path/to/clone1", "/path/to/clone2"]
        mock_get_clones.return_value = mock_clones
        mock_get_branch_info.return_value = {"main": 2}  # All clones on main branch
        mock_get_index_info.return_value = {"dirty": False}

        # Run test
        branch.main(self.args, self.config)

        # Verify new branch creation was called
        mock_create_branch.assert_called_once_with("test-branch", mock_clones)

        # Should print success messages
        success_calls = [
            call
            for call in mock_cprint.call_args_list
            if len(call[0]) > 0 and "Ready for you to make" in str(call[0][0])
        ]
        self.assertTrue(len(success_calls) > 0)

    @patch("builtins.print")
    @patch("shared.branch.cprint")
    @patch("shared.branch.get_clones")
    @patch("shared.branch.get_branch_info")
    @patch("shared.branch.get_index_info")
    def test_main_already_on_target_branch(
        self,
        mock_get_index_info,
        mock_get_branch_info,
        mock_get_clones,
        mock_cprint,
        mock_print,
    ):
        """Test when already on the target branch."""
        # Setup mocks - already on target branch
        mock_clones = ["/path/to/clone1"]
        mock_get_clones.return_value = mock_clones
        mock_get_branch_info.return_value = {
            "test-branch": 1
        }  # Already on target branch
        mock_get_index_info.return_value = {"dirty": False}

        # Run test
        branch.main(self.args, self.config)

        # Should print message about already being on branch
        already_on_calls = [
            call
            for call in mock_print.call_args_list
            if "already on the test-branch branch" in str(call)
        ]
        self.assertTrue(len(already_on_calls) > 0)

    @patch("shared.branch.cprint")
    @patch("shared.branch.get_clones")
    @patch("shared.branch.get_branch_info")
    @patch("shared.branch.get_index_info")
    def test_main_error_different_branches(
        self, mock_get_index_info, mock_get_branch_info, mock_get_clones, mock_cprint
    ):
        """Test error when clones are on different branches."""
        # Setup mocks - clones on different branches
        mock_clones = ["/path/to/clone1", "/path/to/clone2"]
        mock_get_clones.return_value = mock_clones
        mock_get_branch_info.return_value = {
            "branch1": 1,
            "branch2": 1,
        }  # Different branches
        mock_get_index_info.return_value = {"dirty": False}

        # Run test
        branch.main(self.args, self.config)

        # Should print error message
        error_calls = [
            call
            for call in mock_cprint.call_args_list
            if len(call[0]) > 0 and "ERROR" in str(call[0][0])
        ]
        self.assertTrue(len(error_calls) > 0)

        # Should suggest reset
        tip_calls = [
            call
            for call in mock_cprint.call_args_list
            if len(call[0]) > 0 and "TIP:" in str(call[0][0])
        ]
        self.assertTrue(len(tip_calls) > 0)

    @patch("builtins.print")
    @patch("shared.branch.subprocess.run")
    @patch("shared.branch.os.path.isdir")
    @patch("shared.branch.os.path.isfile")
    @patch("shared.branch.os.mkdir")
    @patch("builtins.open")
    def test_create_branch_function(
        self,
        mock_open,
        mock_mkdir,
        mock_isfile,
        mock_isdir,
        mock_subprocess_run,
        mock_print,
    ):
        """Test the create_branch function."""
        # Setup mocks
        clones = ["/path/to/clone1", "/path/to/clone2"]
        branch_name = "test-feature"

        # Mock subprocess calls
        mock_proc_branch = MagicMock()
        mock_proc_branch.stdout = "  main\n* feature-old\n  develop\n"
        mock_proc_checkout = MagicMock()

        mock_subprocess_run.side_effect = [
            mock_proc_branch,
            mock_proc_checkout,
            mock_proc_branch,
            mock_proc_checkout,
        ]

        # Mock file system
        mock_isdir.return_value = True
        mock_isfile.return_value = False  # PR template doesn't exist

        # Run test
        branch.create_branch(branch_name, clones)

        # Verify git commands were called
        self.assertEqual(
            mock_subprocess_run.call_count, 4
        )  # 2 clones × 2 commands each

        # Verify branch creation print message
        create_calls = [
            call
            for call in mock_print.call_args_list
            if "Creating branch test-feature" in str(call)
        ]
        self.assertTrue(len(create_calls) > 0)

    def test_branch_name_sanitization(self):
        """Test that branch names are properly sanitized."""
        # Test with spaces, slashes, colons
        test_args = Namespace(name="test branch/with:special chars")

        with patch("shared.branch.get_clones") as mock_get_clones:
            with patch("shared.branch.get_branch_info") as mock_get_branch_info:
                with patch("shared.branch.get_index_info") as mock_get_index_info:
                    with patch("shared.branch.create_branch") as mock_create_branch:
                        with patch("shared.branch.cprint"):
                            # Setup mocks
                            mock_get_clones.return_value = ["/path/to/clone"]
                            mock_get_branch_info.return_value = {"main": 1}
                            mock_get_index_info.return_value = {"dirty": False}

                            # Run test
                            branch.main(test_args, self.config)

                            # Verify sanitized branch name was used
                            mock_create_branch.assert_called_once()
                            actual_branch_name = mock_create_branch.call_args[0][0]
                            self.assertEqual(
                                actual_branch_name, "test-branch-with-special-chars"
                            )


if __name__ == "__main__":
    unittest.main()
