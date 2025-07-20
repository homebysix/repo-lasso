import os
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to import the shared module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared import sync


class TestSync(unittest.TestCase):
    """Test class for sync module."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = Namespace(verbose=0)
        self.config = {
            "github_username": "testuser",
            "github_org": "testorg",
            "github_token": "fake_token",
        }

    @patch("shared.sync.Github")
    @patch("builtins.print")
    def test_get_user_forks_with_forks(self, mock_print, mock_github_class):
        """Test get_user_forks when user has forks."""
        # Setup org repos
        org_repo1 = MagicMock()
        org_repo1.full_name = "testorg/repo1"
        org_repo2 = MagicMock()
        org_repo2.full_name = "testorg/repo2"
        org_repos = [org_repo1, org_repo2]

        # Setup GitHub API mocks
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_github.get_user.return_value = mock_user

        # Mock user fork
        mock_fork = MagicMock()
        mock_fork.fork = True
        mock_fork.parent.full_name = "testorg/repo1"

        mock_user.get_repos.return_value = [mock_fork]

        # Run test
        result = sync.get_user_forks(org_repos, self.config)

        # Verify result
        self.assertEqual(result, [mock_fork])
        mock_user.get_repos.assert_called_once_with(type="forks")

        # Check print statement
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("1 fork of testorg" in call for call in print_calls))

    @patch("shared.sync.Github")
    @patch("builtins.print")
    def test_get_user_forks_no_forks(self, mock_print, mock_github_class):
        """Test get_user_forks when user has no forks."""
        # Setup org repos
        org_repo = MagicMock()
        org_repo.full_name = "testorg/repo1"
        org_repos = [org_repo]

        # Setup GitHub API mocks
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_github.get_user.return_value = mock_user
        mock_user.get_repos.return_value = []  # No forks

        # Run test
        result = sync.get_user_forks(org_repos, self.config)

        # Verify result
        self.assertEqual(result, [])

        # Check print statement uses correct pluralization
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("0 forks of testorg" in call for call in print_calls))

    def test_parallelize_function(self):
        """Test the parallelize wrapper function."""
        mock_args = ("clone_path", {"config": "data"}, Namespace(), 1, 5)

        with patch("shared.sync.sync_clone") as mock_sync_clone:
            mock_sync_clone.return_value = "test_result"

            result = sync.parallelize(mock_args)

            mock_sync_clone.assert_called_once_with(
                "clone_path", {"config": "data"}, Namespace(), 1, 5
            )
            self.assertEqual(result, "test_result")

    @patch("shared.sync.subprocess.run")
    @patch("shared.sync.cprint")
    @patch("shared.sync.os.path.relpath")
    def test_sync_clone_successful_sync(
        self, mock_relpath, mock_cprint, mock_subprocess_run
    ):
        """Test sync_clone with successful sync operation."""
        # Setup mocks
        clone_path = "/path/to/clone"
        mock_relpath.return_value = "repos/test-repo"

        # Mock subprocess calls
        mock_branch_proc = MagicMock()
        mock_branch_proc.stdout = "  develop\n* main\n  feature\n"

        mock_current_branch_proc = MagicMock()
        mock_current_branch_proc.stdout = "main"

        mock_success_proc = MagicMock()
        mock_success_proc.returncode = 0

        mock_subprocess_run.side_effect = [
            mock_branch_proc,  # git branch
            mock_current_branch_proc,  # git branch --show-current
            mock_success_proc,  # git fetch --all
            mock_success_proc,  # git pull --ff-only
            mock_success_proc,  # git push origin
        ]

        # Run test
        sync.sync_clone(clone_path, self.config, self.args, 1, 3)

        # Verify subprocess calls
        self.assertEqual(mock_subprocess_run.call_count, 5)

        # Verify sync message
        mock_cprint.assert_called_once_with(
            "Syncing clone repos/test-repo (1 of 3)...",
            sync.colors.OKBLUE,
        )

    @patch("shared.sync.subprocess.run")
    @patch("shared.sync.cprint")
    @patch("shared.sync.os.path.relpath")
    def test_sync_clone_fetch_failure(
        self, mock_relpath, mock_cprint, mock_subprocess_run
    ):
        """Test sync_clone when fetch fails."""
        # Setup mocks
        clone_path = "/path/to/clone"
        mock_relpath.return_value = "repos/test-repo"

        # Mock subprocess calls
        mock_branch_proc = MagicMock()
        mock_branch_proc.stdout = "* main\n"

        mock_current_branch_proc = MagicMock()
        mock_current_branch_proc.stdout = "main"

        mock_failed_proc = MagicMock()
        mock_failed_proc.returncode = 1

        mock_subprocess_run.side_effect = [
            mock_branch_proc,  # git branch
            mock_current_branch_proc,  # git branch --show-current
            mock_failed_proc,  # git fetch --all (fails)
        ]

        # Run test
        sync.sync_clone(clone_path, self.config, self.args, 1, 3)

        # Should only make 3 subprocess calls (stops after fetch fails)
        self.assertEqual(mock_subprocess_run.call_count, 3)

        # Should print failure message
        cprint_calls = [call for call in mock_cprint.call_args_list]
        self.assertTrue(
            any("Failed to fetch upstream" in str(call) for call in cprint_calls)
        )

    @patch("shared.sync.subprocess.run")
    @patch("shared.sync.os.path.relpath")
    def test_sync_clone_not_on_default_branch(self, mock_relpath, mock_subprocess_run):
        """Test sync_clone when not on default branch (should only fetch)."""
        # Setup mocks
        clone_path = "/path/to/clone"
        mock_relpath.return_value = "repos/test-repo"

        # Mock subprocess calls
        mock_branch_proc = MagicMock()
        mock_branch_proc.stdout = "  main\n* feature-branch\n"

        mock_current_branch_proc = MagicMock()
        mock_current_branch_proc.stdout = "feature-branch"

        mock_success_proc = MagicMock()
        mock_success_proc.returncode = 0

        mock_subprocess_run.side_effect = [
            mock_branch_proc,  # git branch
            mock_current_branch_proc,  # git branch --show-current
            mock_success_proc,  # git fetch --all
        ]

        # Run test
        sync.sync_clone(clone_path, self.config, self.args, 1, 3)

        # Should only make 3 subprocess calls (no pull/push for non-default branch)
        self.assertEqual(mock_subprocess_run.call_count, 3)

    @patch("shared.sync.get_org_repos")
    @patch("shared.sync.get_user_forks")
    @patch("shared.sync.get_clones")
    @patch("shared.sync.cprint")
    def test_main_basic_flow(
        self, mock_cprint, mock_get_clones, mock_get_user_forks, mock_get_org_repos
    ):
        """Test main function basic flow without missing forks or clones."""
        # Setup mocks
        mock_org_repos = [MagicMock()]
        mock_org_repos[0].full_name = "testorg/repo1"
        mock_get_org_repos.return_value = mock_org_repos

        mock_user_forks = [MagicMock()]
        mock_user_forks[0].parent.full_name = "testorg/repo1"
        mock_user_forks[0].name = "repo1"
        mock_get_user_forks.return_value = mock_user_forks

        mock_clones = ["/path/to/clone1"]
        mock_get_clones.return_value = mock_clones

        with patch("shared.sync.os.path.isdir", return_value=True):
            with patch("shared.sync.ThreadPool") as mock_thread_pool:
                mock_pool = MagicMock()
                mock_thread_pool.return_value.__enter__.return_value = mock_pool

                # Run test
                sync.main(self.args, self.config)

        # Verify key function calls
        mock_get_org_repos.assert_called_once_with(self.config, self.args)
        mock_get_user_forks.assert_called_once_with(mock_org_repos, self.config)
        mock_get_clones.assert_called_once_with(self.config)

        # Verify header print
        mock_cprint.assert_called_with("\nSYNC", sync.colors.OKBLUE)

        # Verify ThreadPool was used for syncing
        mock_pool.map.assert_called_once()


if __name__ == "__main__":
    unittest.main()
