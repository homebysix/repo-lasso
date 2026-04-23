import os
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to import the shared module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared import commit


class TestCommit(unittest.TestCase):
    """Test class for commit module."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = Namespace(message="Test commit message")
        self.config = {"github_username": "testuser", "github_org": "testorg"}

    @patch("shared.commit.get_clones")
    @patch("shared.commit.cprint")
    @patch("shared.commit.subprocess.run")
    @patch("shared.commit.os.path.relpath")
    @patch("builtins.print")
    def test_main_successful_commit(
        self,
        mock_print,
        mock_relpath,
        mock_subprocess_run,
        mock_cprint,
        mock_get_clones,
    ):
        """Test main function with successful commit."""
        # Setup mocks
        mock_clones = ["/path/to/repo1", "/path/to/repo2"]
        mock_get_clones.return_value = mock_clones
        mock_relpath.side_effect = lambda x: f"repos/{os.path.basename(x)}"

        # Mock subprocess calls (git add and git commit for each repo)
        mock_proc = MagicMock()
        mock_subprocess_run.return_value = mock_proc

        # Run test
        commit.main(self.args, self.config)

        # Verify header print
        mock_cprint.assert_called_once_with("\nCOMMIT", commit.colors.OKBLUE)

        # Verify get_clones was called with config
        mock_get_clones.assert_called_once_with(self.config)

        # Verify print statements for each clone
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("repos/repo1" in call for call in print_calls))
        self.assertTrue(any("repos/repo2" in call for call in print_calls))
        self.assertTrue(any("(1 of 2)" in call for call in print_calls))
        self.assertTrue(any("(2 of 2)" in call for call in print_calls))

        # Verify subprocess calls (2 repos × 2 commands each = 4 calls)
        self.assertEqual(mock_subprocess_run.call_count, 4)

        # Check specific git commands
        expected_calls = [
            # First repo: git add --all
            (["git", "-C", "/path/to/repo1", "add", "--all"],),
            # First repo: git commit
            (
                [
                    "git",
                    "-C",
                    "/path/to/repo1",
                    "commit",
                    "--message",
                    "Test commit message",
                ],
            ),
            # Second repo: git add --all
            (["git", "-C", "/path/to/repo2", "add", "--all"],),
            # Second repo: git commit
            (
                [
                    "git",
                    "-C",
                    "/path/to/repo2",
                    "commit",
                    "--message",
                    "Test commit message",
                ],
            ),
        ]

        actual_calls = [call[0] for call in mock_subprocess_run.call_args_list]
        self.assertEqual(actual_calls, expected_calls)

    @patch("shared.commit.get_clones")
    @patch("shared.commit.cprint")
    @patch("shared.commit.subprocess.run")
    @patch("builtins.print")
    def test_main_no_clones(
        self, mock_print, mock_subprocess_run, mock_cprint, mock_get_clones
    ):
        """Test main function when no clones exist."""
        # Setup mocks - no clones
        mock_get_clones.return_value = []

        # Run test
        commit.main(self.args, self.config)

        # Verify header print
        mock_cprint.assert_called_once_with("\nCOMMIT", commit.colors.OKBLUE)

        # Verify get_clones was called
        mock_get_clones.assert_called_once_with(self.config)

        # No subprocess calls should be made
        mock_subprocess_run.assert_not_called()

        # No clone processing print statements
        mock_print.assert_not_called()

    @patch("shared.commit.get_clones")
    @patch("shared.commit.subprocess.run")
    @patch("shared.commit.os.path.relpath")
    @patch("builtins.print")
    def test_main_single_clone(
        self, mock_print, mock_relpath, mock_subprocess_run, mock_get_clones
    ):
        """Test main function with single clone."""
        # Setup mocks
        mock_clones = ["/path/to/single-repo"]
        mock_get_clones.return_value = mock_clones
        mock_relpath.return_value = "repos/single-repo"

        # Run test
        commit.main(self.args, self.config)

        # Verify correct indexing for single repo
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("(1 of 1)" in call for call in print_calls))

        # Verify 2 subprocess calls (add + commit)
        self.assertEqual(mock_subprocess_run.call_count, 2)

    @patch("shared.commit.get_clones")
    @patch("shared.commit.subprocess.run")
    @patch("shared.commit.os.path.relpath")
    def test_main_subprocess_failure_handling(
        self, mock_relpath, mock_subprocess_run, mock_get_clones
    ):
        """Test that subprocess calls use check=False for graceful failure handling."""
        # Setup mocks
        mock_clones = ["/path/to/repo1"]
        mock_get_clones.return_value = mock_clones
        mock_relpath.return_value = "repos/repo1"

        # Mock subprocess to return normal results (not raise exceptions)
        mock_proc_result = MagicMock()
        mock_subprocess_run.return_value = mock_proc_result

        # Run test
        commit.main(self.args, self.config)

        # Verify subprocess.run was called with check=False for both commands
        expected_calls = [
            unittest.mock.call(
                ["git", "-C", "/path/to/repo1", "add", "--all"],
                check=False,
                capture_output=True,
            ),
            unittest.mock.call(
                [
                    "git",
                    "-C",
                    "/path/to/repo1",
                    "commit",
                    "--message",
                    "Test commit message",
                ],
                check=False,
                capture_output=True,
            ),
        ]

        mock_subprocess_run.assert_has_calls(expected_calls)
        self.assertEqual(mock_subprocess_run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
