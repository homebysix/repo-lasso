import os
import subprocess
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

from github.GithubException import GithubException

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

    @patch("builtins.input")
    @patch("builtins.print")
    @patch("shared.sync.cprint")
    @patch("shared.sync.sys.exit")
    def test_create_user_forks_user_consent_yes(
        self, mock_exit, mock_cprint, mock_print, mock_input
    ):
        """Test create_user_forks when user consents to creating forks."""
        # Setup
        mock_input.return_value = "y"

        mock_repo1 = MagicMock()
        mock_repo1.full_name = "testorg/repo1"
        mock_repo1.create_fork.return_value = MagicMock()

        mock_repo2 = MagicMock()
        mock_repo2.full_name = "testorg/repo2"
        mock_repo2.create_fork.return_value = MagicMock()

        repos_to_fork = [mock_repo1, mock_repo2]

        # Run test
        result = list(sync.create_user_forks(repos_to_fork, self.config))

        # Verify
        self.assertEqual(len(result), 2)
        mock_repo1.create_fork.assert_called_once()
        mock_repo2.create_fork.assert_called_once()
        mock_exit.assert_not_called()

        # Verify input prompt
        mock_input.assert_called_once_with(
            "OK to create forks in the testuser GitHub account? [y/n] "
        )

        # Verify print output (repos list and user prompt are printed)
        self.assertTrue(mock_print.called)
        self.assertFalse(mock_cprint.called)  # No warnings in success case

    @patch("builtins.input")
    @patch("builtins.print")
    @patch("shared.sync.cprint")
    @patch("shared.sync.sys.exit")
    def test_create_user_forks_user_consent_no(
        self, mock_exit, mock_cprint, mock_print, mock_input
    ):
        """Test create_user_forks when user declines to create forks."""
        # Setup
        mock_input.return_value = "n"
        mock_exit.side_effect = SystemExit(0)  # Make exit actually raise SystemExit

        mock_repo = MagicMock()
        mock_repo.full_name = "testorg/repo1"
        repos_to_fork = [mock_repo]

        # Run test - the generator function needs to be called and iterated to trigger sys.exit
        generator = sync.create_user_forks(repos_to_fork, self.config)

        # Convert to list to force execution - this should trigger SystemExit
        with self.assertRaises(SystemExit) as context:
            list(generator)

        # Verify exit code
        self.assertEqual(context.exception.code, 0)
        mock_exit.assert_called_once_with(0)
        mock_repo.create_fork.assert_not_called()

        # Verify warning message was printed
        cprint_calls = [call for call in mock_cprint.call_args_list]
        self.assertTrue(
            any("Did not consent to fork repos" in str(call) for call in cprint_calls)
        )

        # Verify regular print was used for repo list
        self.assertTrue(mock_print.called)

    @patch("builtins.input")
    @patch("builtins.print")
    @patch("shared.sync.cprint")
    @patch("shared.sync.sys.exit")
    def test_create_user_forks_github_exception(
        self, mock_exit, mock_cprint, mock_print, mock_input
    ):
        """Test create_user_forks when GitHub API throws an exception."""
        # Setup
        mock_input.return_value = "yes"

        mock_repo1 = MagicMock()
        mock_repo1.full_name = "testorg/repo1"
        mock_repo1.html_url = "https://github.com/testorg/repo1"
        mock_repo1.create_fork.side_effect = GithubException(403, "Forbidden")

        mock_repo2 = MagicMock()
        mock_repo2.full_name = "testorg/repo2"
        mock_repo2.create_fork.return_value = MagicMock()

        repos_to_fork = [mock_repo1, mock_repo2]

        # Run test
        result = list(sync.create_user_forks(repos_to_fork, self.config))

        # Verify - should continue despite exception
        self.assertEqual(len(result), 1)  # Only successful fork returned
        mock_repo1.create_fork.assert_called_once()
        mock_repo2.create_fork.assert_called_once()
        mock_exit.assert_not_called()

        # Verify warning message was printed for failed fork
        cprint_calls = [call for call in mock_cprint.call_args_list]
        self.assertTrue(
            any(
                "Attempt to fork repo testorg/repo1 failed" in str(call)
                for call in cprint_calls
            )
        )

        # Verify regular print was used for repo list
        self.assertTrue(mock_print.called)

    @patch("builtins.input")
    @patch("builtins.print")
    @patch("shared.sync.subprocess.run")
    @patch("shared.sync.os.path.join")
    @patch("shared.sync.os.path.isfile")
    @patch("shared.sync.cprint")
    @patch("shared.sync.sys.exit")
    def test_create_clones_user_consent_yes(
        self,
        mock_exit,
        mock_cprint,
        mock_isfile,
        mock_join,
        mock_subprocess,
        mock_print,
        mock_input,
    ):
        """Test create_clones when user consents to creating clones."""
        # Setup
        mock_input.return_value = "y"
        mock_isfile.return_value = False  # No pre-commit config

        # Mock successful subprocess runs for git commands
        mock_success_proc = MagicMock()
        mock_success_proc.returncode = 0
        mock_subprocess.return_value = mock_success_proc

        # Setup mock fork objects
        mock_fork1 = MagicMock()
        mock_fork1.full_name = "testuser/repo1"
        mock_fork1.name = "repo1"
        mock_fork1.ssh_url = "git@github.com:testuser/repo1.git"
        mock_fork1.parent.ssh_url = "git@github.com:testorg/repo1.git"

        mock_fork2 = MagicMock()
        mock_fork2.full_name = "testuser/repo2"
        mock_fork2.name = "repo2"
        mock_fork2.ssh_url = "git@github.com:testuser/repo2.git"
        mock_fork2.parent.ssh_url = "git@github.com:testorg/repo2.git"

        forks_to_clone = [mock_fork1, mock_fork2]

        # Mock os.path.join to return predictable paths
        mock_join.side_effect = lambda *args: "/".join(args)

        # Run test
        sync.create_clones(forks_to_clone, self.config)

        # Verify subprocess calls - should be 8 calls total (4 per repo)
        # 1. git clone, 2. git remote add, 3. git fetch upstream, 4. git remote set-head
        self.assertEqual(mock_subprocess.call_count, 8)

        # Verify git clone commands
        clone_calls = [
            call for call in mock_subprocess.call_args_list if call[0][0][1] == "clone"
        ]
        self.assertEqual(len(clone_calls), 2)

        # Verify git remote add commands
        remote_calls = [
            call
            for call in mock_subprocess.call_args_list
            if len(call[0][0]) > 3
            and call[0][0][3] == "remote"
            and call[0][0][4] == "add"
        ]
        self.assertEqual(len(remote_calls), 2)

        # Verify git fetch upstream commands
        fetch_calls = [
            call
            for call in mock_subprocess.call_args_list
            if len(call[0][0]) > 3 and call[0][0][3] == "fetch"
        ]
        self.assertEqual(len(fetch_calls), 2)

        # Verify git remote set-head commands
        set_head_calls = [
            call
            for call in mock_subprocess.call_args_list
            if len(call[0][0]) > 4 and call[0][0][4] == "set-head"
        ]
        self.assertEqual(len(set_head_calls), 2)

        mock_exit.assert_not_called()

        # Verify print was used for clone list
        self.assertTrue(mock_print.called)
        self.assertFalse(mock_cprint.called)  # No warnings in success case

    @patch("builtins.input")
    @patch("builtins.print")
    @patch("shared.sync.cprint")
    @patch("shared.sync.sys.exit")
    def test_create_clones_user_consent_no(
        self, mock_exit, mock_cprint, mock_print, mock_input
    ):
        """Test create_clones when user declines to create clones."""
        # Setup
        mock_input.return_value = "no"
        mock_exit.side_effect = SystemExit(0)  # Make exit actually raise SystemExit

        mock_fork = MagicMock()
        mock_fork.full_name = "testuser/repo1"
        mock_fork.name = "repo1"
        forks_to_clone = [mock_fork]

        # Run test - should raise SystemExit
        with self.assertRaises(SystemExit) as context:
            sync.create_clones(forks_to_clone, self.config)

        # Verify exit code and that exit was called
        self.assertEqual(context.exception.code, 0)
        mock_exit.assert_called_once_with(0)

        # Verify warning message was printed
        cprint_calls = [call for call in mock_cprint.call_args_list]
        self.assertTrue(
            any("Did not consent to clone forks" in str(call) for call in cprint_calls)
        )

        # Verify regular print was used for clone list
        self.assertTrue(mock_print.called)

    @patch("builtins.input")
    @patch("builtins.print")
    @patch("shared.sync.subprocess.run")
    @patch("shared.sync.os.path.join")
    @patch("shared.sync.os.path.isfile")
    def test_create_clones_with_precommit_config(
        self, mock_isfile, mock_join, mock_subprocess, mock_print, mock_input
    ):
        """Test create_clones when repos have pre-commit configuration."""
        # Setup
        mock_input.return_value = "y"

        # Mock fork object
        mock_fork = MagicMock()
        mock_fork.full_name = "testuser/repo1"
        mock_fork.name = "repo1"
        mock_fork.ssh_url = "git@github.com:testuser/repo1.git"
        mock_fork.parent.ssh_url = "git@github.com:testorg/repo1.git"

        forks_to_clone = [mock_fork]

        # Mock os.path.join and isfile
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_isfile.return_value = True  # Pre-commit config exists

        # Mock successful subprocess runs
        mock_success_proc = MagicMock()
        mock_success_proc.returncode = 0
        mock_subprocess.return_value = mock_success_proc

        # Run test
        sync.create_clones(forks_to_clone, self.config)

        # Verify pre-commit install was called (5th subprocess call)
        self.assertEqual(mock_subprocess.call_count, 5)

        # Last call should be pre-commit install
        last_call = mock_subprocess.call_args_list[-1]
        self.assertEqual(last_call[0][0], ["pre-commit", "install"])
        self.assertEqual(
            last_call[1]["check"], False
        )  # Should not check=True for pre-commit

        # Verify regular print was used
        self.assertTrue(mock_print.called)

    @patch("builtins.input")
    @patch("builtins.print")
    @patch("shared.sync.subprocess.run")
    @patch("shared.sync.os.path.join")
    @patch("shared.sync.os.path.isfile")
    def test_create_clones_precommit_not_found(
        self, mock_isfile, mock_join, mock_subprocess, mock_print, mock_input
    ):
        """Test create_clones when pre-commit is not installed."""
        # Setup
        mock_input.return_value = "y"

        # Mock fork object
        mock_fork = MagicMock()
        mock_fork.full_name = "testuser/repo1"
        mock_fork.name = "repo1"
        mock_fork.ssh_url = "git@github.com:testuser/repo1.git"
        mock_fork.parent.ssh_url = "git@github.com:testorg/repo1.git"

        forks_to_clone = [mock_fork]

        # Mock os.path.join and isfile
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_isfile.return_value = True  # Pre-commit config exists

        # Mock git commands succeed, but pre-commit fails with FileNotFoundError
        def subprocess_side_effect(cmd, **_kwargs):
            if cmd == ["pre-commit", "install"]:
                raise FileNotFoundError("pre-commit not found")
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

        # Run test - should not raise exception
        sync.create_clones(forks_to_clone, self.config)

        # Verify git commands were still called (should be 4 calls)
        self.assertEqual(mock_subprocess.call_count, 5)  # 4 git + 1 failed pre-commit

        # Verify regular print was used
        self.assertTrue(mock_print.called)

    @patch("builtins.input")
    @patch("builtins.print")
    @patch("shared.sync.subprocess.run")
    @patch("shared.sync.os.path.join")
    @patch("shared.sync.os.path.isfile")
    def test_create_clones_git_command_failure(
        self, mock_isfile, mock_join, mock_subprocess, mock_print, mock_input
    ):
        """Test create_clones when git commands fail."""
        # Setup
        mock_input.return_value = "y"

        # Mock fork object
        mock_fork = MagicMock()
        mock_fork.full_name = "testuser/repo1"
        mock_fork.name = "repo1"
        mock_fork.ssh_url = "git@github.com:testuser/repo1.git"
        mock_fork.parent.ssh_url = "git@github.com:testorg/repo1.git"

        forks_to_clone = [mock_fork]

        # Mock os.path.join
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_isfile.return_value = False

        # Mock git clone to fail
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git clone")

        # Run test - should raise exception since check=True
        with self.assertRaises(subprocess.CalledProcessError):
            sync.create_clones(forks_to_clone, self.config)

        # Verify regular print was used before failure
        self.assertTrue(mock_print.called)

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
