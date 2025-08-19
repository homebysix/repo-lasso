import argparse
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to import the shared module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared import (
    build_argument_parser,
    colors,
    cprint,
    get_branch_info,
    get_clones,
    get_config,
    get_default_branch,
    get_index_info,
    get_org_repos,
    readable_time,
    trim_leading_org,
)

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

    def test_build_argument_parser_import_check(self):
        """Test that build_argument_parser function exists and is callable."""
        # Just verify the function exists and is callable
        self.assertTrue(callable(build_argument_parser))
        # We can't easily test the full parser creation without mocking all the subcommand functions
        # This test just ensures the function is importable and callable

    def test_argument_parser_constants(self):
        """Test that argument parser uses expected constants."""
        from shared import LOGO, __version__

        # Test that constants are defined correctly
        self.assertIsInstance(__version__, str)
        self.assertIn("1.", __version__)  # Should be version 1.x
        self.assertIsInstance(LOGO, str)
        self.assertIn(__version__, LOGO)  # Version should appear in logo
        self.assertTrue(len(LOGO) > 50)  # Logo should be a substantial ASCII art string

    @patch("builtins.print")
    def test_cprint_basic(self, mock_print):
        """Test cprint function with basic color output."""
        cprint("test message", colors.OKBLUE)

        # Verify print was called
        mock_print.assert_called_once()

        # Check that the message contains color codes
        call_args = str(mock_print.call_args)
        self.assertIn("test message", call_args)
        self.assertIn("\\x1b[94m", call_args)  # OKBLUE color code (escaped)
        self.assertIn("\\x1b[0m", call_args)  # ENDC color code (escaped)

    @patch("builtins.print")
    def test_cprint_with_indent(self, mock_print):
        """Test cprint function with indentation."""
        cprint("test message", colors.WARNING, indent_level=2)

        # Verify print was called
        mock_print.assert_called_once()

        # Check for indentation (2 spaces)
        call_args = str(mock_print.call_args)
        self.assertIn("  ", call_args)  # Should have indentation

    @patch("shared.glob")
    @patch("shared.os.path.isdir")
    @patch("builtins.print")
    def test_get_clones_with_clones(self, mock_print, mock_isdir, mock_glob):
        """Test get_clones when clones exist."""
        config = {"github_org": "testorg"}

        # Mock glob to return some paths
        mock_glob.return_value = ["/path/to/repo1", "/path/to/repo2"]

        # Mock isdir to return True for .git directories
        mock_isdir.side_effect = lambda path: path.endswith("/.git")

        result = get_clones(config)

        # Should return the clones that have .git directories
        self.assertEqual(result, ["/path/to/repo1", "/path/to/repo2"])

        # Should print about clones found
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("2 repo clones are cached" in call for call in print_calls))

    @patch("shared.glob")
    @patch("shared.os.path.isdir")
    @patch("builtins.print")
    def test_get_clones_no_clones(self, mock_print, mock_isdir, mock_glob):
        """Test get_clones when no clones exist."""
        config = {"github_org": "testorg"}

        # Mock glob to return empty list
        mock_glob.return_value = []

        result = get_clones(config)

        # Should return empty list
        self.assertEqual(result, [])

        # Should print helpful tip
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("0 repo clones are cached" in call for call in print_calls))

    @patch("shared.subprocess.run")
    def test_get_branch_info(self, mock_subprocess_run):
        """Test get_branch_info function."""
        clones = ["/path/to/clone1", "/path/to/clone2"]

        # Mock subprocess calls
        mock_proc1 = MagicMock()
        mock_proc1.stdout = "main"
        mock_proc2 = MagicMock()
        mock_proc2.stdout = "feature-branch"

        mock_subprocess_run.side_effect = [mock_proc1, mock_proc2]

        result = get_branch_info(clones)

        expected = {"main": ["/path/to/clone1"], "feature-branch": ["/path/to/clone2"]}

        self.assertEqual(result, expected)
        self.assertEqual(mock_subprocess_run.call_count, 2)

    @patch("shared.subprocess.run")
    def test_get_index_info_clean_and_dirty(self, mock_subprocess_run):
        """Test get_index_info function with clean and dirty repos."""
        clones = ["/path/to/clean", "/path/to/dirty"]

        # Mock subprocess calls - first returns empty (clean), second returns changes (dirty)
        mock_proc1 = MagicMock()
        mock_proc1.stdout = ""  # Clean repo
        mock_proc2 = MagicMock()
        mock_proc2.stdout = " M some_file.py\n"  # Dirty repo

        mock_subprocess_run.side_effect = [mock_proc1, mock_proc2]

        result = get_index_info(clones)

        expected = {"clean": ["/path/to/clean"], "dirty": ["/path/to/dirty"]}

        self.assertEqual(result, expected)
        self.assertEqual(mock_subprocess_run.call_count, 2)

    @patch("shared.Github")
    @patch("builtins.print")
    def test_get_org_repos_basic(self, mock_print, mock_github_class):
        """Test get_org_repos function basic functionality."""
        config = {"github_token": "fake_token", "github_org": "testorg"}
        args = argparse.Namespace(verbose=0)

        # Mock GitHub API
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        # Mock repo list
        mock_repo1 = MagicMock()
        mock_repo1.name = "repo1"
        mock_repo1.full_name = "testorg/repo1"
        mock_repo1.archived = False
        mock_repo1.private = False

        mock_repo2 = MagicMock()
        mock_repo2.name = "repo2"
        mock_repo2.full_name = "testorg/repo2"
        mock_repo2.archived = True  # This should be skipped
        mock_repo2.private = False

        mock_repos = MagicMock()
        mock_repos.totalCount = 50
        mock_repos.__iter__ = lambda self: iter([mock_repo1, mock_repo2])
        mock_org.get_repos.return_value = mock_repos

        result = get_org_repos(config, args)

        # Should only return non-archived repos
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], mock_repo1)

        # Verify GitHub API calls
        mock_github.get_organization.assert_called_once_with("testorg")

    @patch("shared.Github")
    @patch("builtins.print")
    def test_get_org_repos_with_exclusions(self, mock_print, mock_github_class):
        """Test get_org_repos with excluded repos."""
        config = {
            "github_token": "fake_token",
            "github_org": "testorg",
            "excluded_repos": ["excluded-repo"],
        }
        args = argparse.Namespace(verbose=1)

        # Mock GitHub API
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        # Mock repo list including excluded repo
        mock_repo1 = MagicMock()
        mock_repo1.name = "repo1"
        mock_repo1.full_name = "testorg/repo1"
        mock_repo1.archived = False
        mock_repo1.private = False

        mock_excluded = MagicMock()
        mock_excluded.name = "excluded-repo"
        mock_excluded.full_name = "testorg/excluded-repo"
        mock_excluded.archived = False
        mock_excluded.private = False

        mock_repos = MagicMock()
        mock_repos.totalCount = 50
        mock_repos.__iter__ = lambda self: iter([mock_repo1, mock_excluded])
        mock_org.get_repos.return_value = mock_repos

        result = get_org_repos(config, args)

        # Should only return non-excluded repos
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], mock_repo1)

        # Should print exclusion message with verbose=1
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(
            any(
                "Skipping testorg/excluded-repo (excluded)" in call
                for call in print_calls
            )
        )

    @patch("shared.subprocess.run")
    def test_get_default_branch_success(self, mock_subprocess_run):
        """Test get_default_branch function with successful upstream HEAD detection."""
        # Setup mock for successful git symbolic-ref command
        mock_proc = MagicMock()
        mock_proc.stdout = "refs/remotes/upstream/main"
        mock_subprocess_run.return_value = mock_proc

        # Test
        result = get_default_branch("/path/to/repo")

        # Verify
        self.assertEqual(result, "main")
        mock_subprocess_run.assert_called_once_with(
            [
                "git",
                "-C",
                "/path/to/repo",
                "symbolic-ref",
                "refs/remotes/upstream/HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("shared.subprocess.run")
    def test_get_default_branch_master_branch(self, mock_subprocess_run):
        """Test get_default_branch function with master as upstream default branch."""
        # Setup mock for git symbolic-ref command returning master
        mock_proc = MagicMock()
        mock_proc.stdout = "refs/remotes/upstream/master"
        mock_subprocess_run.return_value = mock_proc

        # Test
        result = get_default_branch("/path/to/repo")

        # Verify
        self.assertEqual(result, "master")
        mock_subprocess_run.assert_called_once_with(
            [
                "git",
                "-C",
                "/path/to/repo",
                "symbolic-ref",
                "refs/remotes/upstream/HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("shared.subprocess.run")
    def test_get_default_branch_custom_branch(self, mock_subprocess_run):
        """Test get_default_branch function with custom default branch name."""
        # Setup mock for git symbolic-ref command returning custom branch
        mock_proc = MagicMock()
        mock_proc.stdout = "refs/remotes/upstream/develop"
        mock_subprocess_run.return_value = mock_proc

        # Test
        result = get_default_branch("/path/to/repo")

        # Verify
        self.assertEqual(result, "develop")

    @patch("shared.subprocess.run")
    def test_get_default_branch_with_whitespace(self, mock_subprocess_run):
        """Test get_default_branch function handles output with whitespace."""
        # Setup mock for git symbolic-ref command with whitespace
        mock_proc = MagicMock()
        mock_proc.stdout = "  refs/remotes/upstream/main\n  "
        mock_subprocess_run.return_value = mock_proc

        # Test
        result = get_default_branch("/path/to/repo")

        # Verify - should strip whitespace and extract branch name
        self.assertEqual(result, "main")

    @patch("shared.subprocess.run")
    def test_get_default_branch_subprocess_error(self, mock_subprocess_run):
        """Test get_default_branch function when git command fails."""
        # Setup mock to raise subprocess.CalledProcessError
        import subprocess

        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            1, "git symbolic-ref"
        )

        # Test - should raise the exception
        with self.assertRaises(subprocess.CalledProcessError) as context:
            get_default_branch("/path/to/repo")

        # Verify exception details
        self.assertEqual(context.exception.returncode, 1)
        self.assertEqual(context.exception.cmd, "git symbolic-ref")

    @patch("shared.subprocess.run")
    def test_get_default_branch_no_upstream_remote(self, mock_subprocess_run):
        """Test get_default_branch function when upstream remote doesn't exist."""
        # Setup mock to raise subprocess.CalledProcessError for missing upstream
        import subprocess

        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            128, "git symbolic-ref"
        )

        # Test - should raise the exception
        with self.assertRaises(subprocess.CalledProcessError) as context:
            get_default_branch("/path/to/missing-upstream")

        # Verify exception details
        self.assertEqual(context.exception.returncode, 128)
        self.assertEqual(context.exception.cmd, "git symbolic-ref")

    def test_get_default_branch_function_exists(self):
        """Test that get_default_branch function exists and is callable."""
        # Basic check that the function was imported correctly
        self.assertTrue(callable(get_default_branch))
        self.assertEqual(get_default_branch.__name__, "get_default_branch")


if __name__ == "__main__":
    unittest.main()
