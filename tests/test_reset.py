import os
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to import the shared module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared import reset


class TestReset(unittest.TestCase):
    """Test class for reset module."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = Namespace()  # Reset doesn't use any command line args
        self.config = {"github_username": "testuser", "github_org": "testorg"}

    @patch("shared.reset.get_clones")
    @patch("shared.reset.cprint")
    @patch("shared.reset.subprocess.run")
    @patch("shared.reset.os.path.relpath")
    @patch("builtins.print")
    def test_main_with_main_branch(
        self,
        mock_print,
        mock_relpath,
        mock_subprocess_run,
        mock_cprint,
        mock_get_clones,
    ):
        """Test main function with repositories using 'main' as default branch."""
        # Setup mocks
        mock_clones = ["/path/to/repo1", "/path/to/repo2"]
        mock_get_clones.return_value = mock_clones
        mock_relpath.side_effect = lambda x: f"repos/{os.path.basename(x)}"

        # Mock git branch command output (main branch exists)
        mock_branch_proc = MagicMock()
        mock_branch_proc.stdout = "  develop\n* feature-branch\n  main\n"

        mock_other_proc = MagicMock()

        # First call returns branch info, others are git operations
        mock_subprocess_run.side_effect = [
            mock_branch_proc,  # git branch for repo1
            mock_other_proc,  # git reset --hard for repo1
            mock_other_proc,  # git checkout main for repo1
            mock_other_proc,  # git reset --hard for repo1 (second time)
            mock_other_proc,  # git clean -xdf for repo1
            mock_branch_proc,  # git branch for repo2
            mock_other_proc,  # git reset --hard for repo2
            mock_other_proc,  # git checkout main for repo2
            mock_other_proc,  # git reset --hard for repo2 (second time)
            mock_other_proc,  # git clean -xdf for repo2
        ]

        # Run test
        reset.main(self.args, self.config)

        # Verify header print
        mock_cprint.assert_called_once_with("\nSTATUS", reset.colors.OKBLUE)

        # Verify get_clones was called
        mock_get_clones.assert_called_once_with(self.config)

        # Verify print statements for each clone
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(
            any("repos/repo1" in call and "(1 of 2)" in call for call in print_calls)
        )
        self.assertTrue(
            any("repos/repo2" in call and "(2 of 2)" in call for call in print_calls)
        )

        # Verify subprocess calls (2 repos × 5 commands each = 10 calls)
        self.assertEqual(mock_subprocess_run.call_count, 10)

        # Check some specific git commands
        expected_calls = [
            # First repo: git branch
            (["git", "-C", "/path/to/repo1", "branch"],),
            # First repo: git reset --hard
            (["git", "-C", "/path/to/repo1", "reset", "--hard"],),
            # First repo: git checkout main
            (["git", "-C", "/path/to/repo1", "checkout", "main"],),
        ]

        actual_calls = [call[0] for call in mock_subprocess_run.call_args_list[:3]]
        self.assertEqual(actual_calls, expected_calls)

    @patch("shared.reset.get_clones")
    @patch("shared.reset.subprocess.run")
    @patch("shared.reset.os.path.relpath")
    def test_main_with_master_branch(
        self, mock_relpath, mock_subprocess_run, mock_get_clones
    ):
        """Test main function with repositories using 'master' as default branch."""
        # Setup mocks
        mock_clones = ["/path/to/legacy-repo"]
        mock_get_clones.return_value = mock_clones
        mock_relpath.return_value = "repos/legacy-repo"

        # Mock git branch command output (no main branch, has master)
        mock_branch_proc = MagicMock()
        mock_branch_proc.stdout = "  develop\n* feature-branch\n  master\n"

        mock_other_proc = MagicMock()

        mock_subprocess_run.side_effect = [
            mock_branch_proc,  # git branch
            mock_other_proc,  # git reset --hard
            mock_other_proc,  # git checkout master
            mock_other_proc,  # git reset --hard (second time)
            mock_other_proc,  # git clean -xdf
        ]

        with patch("builtins.print"):
            with patch("shared.reset.cprint"):
                # Run test
                reset.main(self.args, self.config)

        # Verify master branch checkout
        checkout_calls = [
            call
            for call in mock_subprocess_run.call_args_list
            if "checkout" in str(call)
        ]
        self.assertTrue(any("master" in str(call) for call in checkout_calls))

    @patch("shared.reset.get_clones")
    @patch("shared.reset.subprocess.run")
    def test_main_no_clones(self, mock_subprocess_run, mock_get_clones):
        """Test main function when no clones exist."""
        # Setup mocks - no clones
        mock_get_clones.return_value = []

        with patch("builtins.print"):
            with patch("shared.reset.cprint") as mock_cprint:
                # Run test
                reset.main(self.args, self.config)

        # Verify header print
        mock_cprint.assert_called_once_with("\nSTATUS", reset.colors.OKBLUE)

        # Verify get_clones was called
        mock_get_clones.assert_called_once_with(self.config)

        # No subprocess calls should be made
        mock_subprocess_run.assert_not_called()

    @patch("shared.reset.get_clones")
    @patch("shared.reset.subprocess.run")
    @patch("shared.reset.os.path.relpath")
    def test_main_git_commands_sequence(
        self, mock_relpath, mock_subprocess_run, mock_get_clones
    ):
        """Test that git commands are executed in the correct sequence."""
        # Setup mocks
        mock_clones = ["/path/to/single-repo"]
        mock_get_clones.return_value = mock_clones
        mock_relpath.return_value = "repos/single-repo"

        # Mock git branch command output
        mock_branch_proc = MagicMock()
        mock_branch_proc.stdout = "  main\n* feature-branch\n"

        mock_other_proc = MagicMock()

        mock_subprocess_run.side_effect = [
            mock_branch_proc,  # git branch
            mock_other_proc,  # git reset --hard (first)
            mock_other_proc,  # git checkout main
            mock_other_proc,  # git reset --hard (second)
            mock_other_proc,  # git clean -xdf
        ]

        with patch("builtins.print"):
            with patch("shared.reset.cprint"):
                # Run test
                reset.main(self.args, self.config)

        # Verify exact command sequence
        expected_commands = [
            ["git", "-C", "/path/to/single-repo", "branch"],
            ["git", "-C", "/path/to/single-repo", "reset", "--hard"],
            ["git", "-C", "/path/to/single-repo", "checkout", "main"],
            ["git", "-C", "/path/to/single-repo", "reset", "--hard"],
            ["git", "-C", "/path/to/single-repo", "clean", "-xdf"],
        ]

        actual_commands = [call[0][0] for call in mock_subprocess_run.call_args_list]
        self.assertEqual(actual_commands, expected_commands)

        # Verify 5 commands total
        self.assertEqual(mock_subprocess_run.call_count, 5)


if __name__ == "__main__":
    unittest.main()
