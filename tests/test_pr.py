import os
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, mock_open, patch

# Add the parent directory to sys.path to import the shared module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from github import BadCredentialsException, GithubException, RateLimitExceededException

from shared import RateLimitExceededError, pr


class TestPr(unittest.TestCase):
    """Test class for pr module."""

    def setUp(self):
        """Set up test fixtures."""
        self.args = Namespace(template=None)
        self.config = {
            "github_username": "testuser",
            "github_org": "testorg",
            "github_token": "fake_token",
        }

    def test_load_pr_template_with_title(self):
        """Test loading PR template with title."""
        template_content = "# Test Title\n\nThis is the body of the PR template."

        with patch("builtins.open", mock_open(read_data=template_content)):
            title, body = pr.load_pr_template("fake_path.md")

        self.assertEqual(title, "Test Title")
        self.assertEqual(body, "This is the body of the PR template.")

    def test_load_pr_template_without_title(self):
        """Test loading PR template without title header."""
        template_content = "This is just body content without a title header."

        with patch("builtins.open", mock_open(read_data=template_content)):
            # This should raise an UnboundLocalError due to the bug in load_pr_template
            # The function doesn't handle the case where content doesn't start with "# "
            with self.assertRaises(UnboundLocalError):
                pr.load_pr_template("fake_path.md")

    @patch("shared.pr.github_rate_limit_wait")
    @patch("shared.pr.sleep")
    @patch("shared.pr.Github")
    @patch("shared.pr.os.path.isfile")
    def test_open_pull_request_success(
        self, mock_isfile, mock_github_class, mock_sleep, mock_rate_limit_wait
    ):
        """Test successful pull request creation."""
        # Setup mocks
        mock_isfile.return_value = False  # No template file

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user

        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        mock_repo = MagicMock()
        mock_org.get_repo.return_value = mock_repo

        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/testorg/testrepo/pull/1"
        mock_repo.create_pull.return_value = mock_pr

        with patch("builtins.print"):
            # Run test
            result = pr.open_pull_request(
                "/path/to/testrepo", "main", "feature-branch", self.args, self.config
            )

        # Verify result
        self.assertEqual(result, mock_pr)
        mock_repo.create_pull.assert_called_once_with(
            base="main", head="testuser:feature-branch", title="feature-branch", body=""
        )
        mock_sleep.assert_called_once_with(3)
        mock_rate_limit_wait.assert_called_once_with(self.config)

    @patch("shared.pr.github_rate_limit_wait")
    @patch("shared.pr.Github")
    @patch("shared.pr.os.path.isfile")
    @patch("shared.pr.load_pr_template")
    def test_open_pull_request_with_template(
        self, mock_load_template, mock_isfile, mock_github_class, mock_rate_limit_wait
    ):
        """Test pull request creation with template file."""
        # Setup mocks
        mock_isfile.return_value = True  # Template file exists
        mock_load_template.return_value = ("Custom Title", "Custom body content")

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user

        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        mock_repo = MagicMock()
        mock_org.get_repo.return_value = mock_repo

        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/testorg/testrepo/pull/1"
        mock_repo.create_pull.return_value = mock_pr

        with patch("builtins.print"):
            with patch("shared.pr.sleep"):
                # Run test
                result = pr.open_pull_request(
                    "/path/to/testrepo",
                    "main",
                    "feature-branch",
                    self.args,
                    self.config,
                )

        # Verify result
        self.assertEqual(result, mock_pr)
        mock_load_template.assert_called_once()
        mock_repo.create_pull.assert_called_once_with(
            base="main",
            head="testuser:feature-branch",
            title="Custom Title",
            body="Custom body content",
        )

    @patch("shared.pr.os.path.isdir")
    @patch("shared.pr.os.path.isfile")
    @patch("builtins.open", new_callable=mock_open)
    @patch("shared.pr.json.dumps")
    def test_log_initiative_new_branch(
        self, mock_json_dumps, mock_file_open, mock_isfile, mock_isdir
    ):
        """Test logging initiative for new branch."""
        # Setup mocks
        mock_isdir.return_value = True
        mock_isfile.return_value = False  # No existing file
        mock_json_dumps.return_value = '{"test": "data"}'

        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/testorg/testrepo/pull/1"

        # Run test
        pr.log_initiative(mock_pr, "feature-branch", self.config)

        # Verify calls
        mock_json_dumps.assert_called_once()
        mock_file_open.assert_called_once()

    @patch("shared.pr.get_clones")
    @patch("shared.pr.cprint")
    @patch("shared.pr.subprocess.run")
    @patch("shared.pr.open_pull_request")
    @patch("shared.pr.log_initiative")
    @patch("shared.pr.os.path.relpath")
    def test_main_no_commits_ahead(
        self,
        mock_relpath,
        mock_log_initiative,
        mock_open_pr,
        mock_subprocess_run,
        mock_cprint,
        mock_get_clones,
    ):
        """Test main function when no commits are ahead of default branch."""
        # Setup mocks
        mock_clones = ["/path/to/repo1"]
        mock_get_clones.return_value = mock_clones
        mock_relpath.return_value = "repos/repo1"

        # Mock subprocess calls
        mock_branch_proc = MagicMock()
        mock_branch_proc.stdout = "  main\n* feature-branch\n"

        mock_current_branch_proc = MagicMock()
        mock_current_branch_proc.stdout = "feature-branch"

        mock_status_proc = MagicMock()
        mock_status_proc.stdout = ""  # No commits ahead

        mock_subprocess_run.side_effect = [
            mock_branch_proc,
            mock_current_branch_proc,
            mock_status_proc,
        ]

        with patch("builtins.print"):
            # Run test
            pr.main(self.args, self.config)

        # Verify header print and basic flow
        mock_cprint.assert_called_with("\nPULL REQUESTS", pr.colors.OKBLUE)
        mock_get_clones.assert_called_once_with(self.config)

        # Should not attempt to open PR since no commits ahead
        mock_open_pr.assert_not_called()
        mock_log_initiative.assert_not_called()

    @patch("shared.pr.get_clones")
    @patch("shared.pr.subprocess.run")
    @patch("shared.pr.open_pull_request")
    @patch("shared.pr.log_initiative")
    @patch("shared.pr.os.path.relpath")
    def test_main_with_commits_ahead(
        self,
        mock_relpath,
        mock_log_initiative,
        mock_open_pr,
        mock_subprocess_run,
        mock_get_clones,
    ):
        """Test main function when commits are ahead and PR should be created."""
        # Setup mocks
        mock_clones = ["/path/to/repo1"]
        mock_get_clones.return_value = mock_clones
        mock_relpath.return_value = "repos/repo1"

        # Mock subprocess calls
        mock_branch_proc = MagicMock()
        mock_branch_proc.stdout = "  main\n* feature-branch\n"

        mock_current_branch_proc = MagicMock()
        mock_current_branch_proc.stdout = "feature-branch"

        mock_status_proc = MagicMock()
        mock_status_proc.stdout = "abc1234 Some commit message"  # Has commits ahead

        mock_push_proc = MagicMock()

        mock_subprocess_run.side_effect = [
            mock_branch_proc,
            mock_current_branch_proc,
            mock_status_proc,
            mock_push_proc,
        ]

        mock_pr_obj = MagicMock()
        mock_open_pr.return_value = mock_pr_obj

        with patch("builtins.print"):
            with patch("shared.pr.cprint"):
                # Run test
                pr.main(self.args, self.config)

        # Verify PR creation flow
        mock_open_pr.assert_called_once()
        mock_log_initiative.assert_called_once_with(
            mock_pr_obj, "feature-branch", self.config
        )

    @patch("shared.pr.github_rate_limit_wait")
    @patch("shared.pr.Github")
    @patch("shared.pr.os.path.isfile")
    def test_open_pull_request_rate_limit_exceeded_error(
        self, mock_isfile, mock_github_class, mock_rate_limit_wait
    ):
        """Test pull request creation when rate limit wait raises error."""
        # Setup mocks
        mock_isfile.return_value = False

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user

        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        mock_repo = MagicMock()
        mock_org.get_repo.return_value = mock_repo

        # Rate limit wait raises error
        mock_rate_limit_wait.side_effect = RateLimitExceededError(
            "Rate limit exceeded after 10 attempts"
        )

        with patch("builtins.print"):
            with self.assertRaises(RateLimitExceededError):
                pr.open_pull_request(
                    "/path/to/testrepo",
                    "main",
                    "feature-branch",
                    self.args,
                    self.config,
                )

    @patch("shared.pr.github_rate_limit_wait")
    @patch("shared.pr.Github")
    @patch("shared.pr.os.path.isfile")
    def test_open_pull_request_rate_limit_exception(
        self, mock_isfile, mock_github_class, mock_rate_limit_wait
    ):
        """Test pull request creation when GitHub raises RateLimitExceededException."""
        # Setup mocks
        mock_isfile.return_value = False

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user

        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        mock_repo = MagicMock()
        mock_org.get_repo.return_value = mock_repo

        # create_pull raises RateLimitExceededException
        mock_repo.create_pull.side_effect = RateLimitExceededException(403, {}, {})

        mock_rate_limit = MagicMock()
        mock_github.get_rate_limit.return_value = mock_rate_limit

        with patch("builtins.print"):
            with self.assertRaises(RateLimitExceededException):
                pr.open_pull_request(
                    "/path/to/testrepo",
                    "main",
                    "feature-branch",
                    self.args,
                    self.config,
                )

    @patch("shared.pr.github_rate_limit_wait")
    @patch("shared.pr.Github")
    @patch("shared.pr.os.path.isfile")
    def test_open_pull_request_bad_credentials(
        self, mock_isfile, mock_github_class, mock_rate_limit_wait
    ):
        """Test pull request creation with bad credentials."""
        # Setup mocks
        mock_isfile.return_value = False

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user

        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        mock_repo = MagicMock()
        mock_org.get_repo.return_value = mock_repo

        # create_pull raises BadCredentialsException
        error_data = {"message": "Bad credentials"}
        mock_repo.create_pull.side_effect = BadCredentialsException(401, error_data, {})

        with patch("builtins.print"):
            with self.assertRaises(BadCredentialsException):
                pr.open_pull_request(
                    "/path/to/testrepo",
                    "main",
                    "feature-branch",
                    self.args,
                    self.config,
                )

    @patch("shared.pr.github_rate_limit_wait")
    @patch("shared.pr.Github")
    @patch("shared.pr.os.path.isfile")
    def test_open_pull_request_permission_denied(
        self, mock_isfile, mock_github_class, mock_rate_limit_wait
    ):
        """Test pull request creation with permission denied error."""
        # Setup mocks
        mock_isfile.return_value = False

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user

        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        mock_repo = MagicMock()
        mock_org.get_repo.return_value = mock_repo

        # create_pull raises 403 with "not accessible" message
        error_data = {
            "message": "Resource not accessible by personal access token",
            "documentation_url": "https://docs.github.com/rest/pulls/pulls#create-a-pull-request",
        }
        mock_repo.create_pull.side_effect = GithubException(403, error_data, {})

        with patch("builtins.print"):
            with self.assertRaises(GithubException):
                pr.open_pull_request(
                    "/path/to/testrepo",
                    "main",
                    "feature-branch",
                    self.args,
                    self.config,
                )

    @patch("shared.pr.github_rate_limit_wait")
    @patch("shared.pr.Github")
    @patch("shared.pr.os.path.isfile")
    def test_open_pull_request_other_403_error(
        self, mock_isfile, mock_github_class, mock_rate_limit_wait
    ):
        """Test pull request creation with other 403 error (not permission denied)."""
        # Setup mocks
        mock_isfile.return_value = False

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user

        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        mock_repo = MagicMock()
        mock_org.get_repo.return_value = mock_repo

        # create_pull raises 403 with different message
        error_data = {"message": "Some other forbidden error"}
        mock_repo.create_pull.side_effect = GithubException(403, error_data, {})

        with patch("builtins.print"):
            with self.assertRaises(GithubException):
                pr.open_pull_request(
                    "/path/to/testrepo",
                    "main",
                    "feature-branch",
                    self.args,
                    self.config,
                )

    @patch("shared.pr.github_rate_limit_wait")
    @patch("shared.pr.sleep")
    @patch("shared.pr.Github")
    @patch("shared.pr.os.path.isfile")
    def test_open_pull_request_duplicate_pr_422(
        self, mock_isfile, mock_github_class, mock_sleep, mock_rate_limit_wait
    ):
        """Test pull request creation when PR already exists (422)."""
        # Setup mocks
        mock_isfile.return_value = False

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user

        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        mock_repo = MagicMock()
        mock_org.get_repo.return_value = mock_repo

        # create_pull raises 422 error
        error_data = {"message": "Validation Failed"}
        mock_repo.create_pull.side_effect = GithubException(422, error_data, {})

        with patch("builtins.print"):
            result = pr.open_pull_request(
                "/path/to/testrepo",
                "main",
                "feature-branch",
                self.args,
                self.config,
            )

        # Should return None but not raise
        self.assertIsNone(result)

    @patch("shared.pr.github_rate_limit_wait")
    @patch("shared.pr.sleep")
    @patch("shared.pr.Github")
    @patch("shared.pr.os.path.isfile")
    def test_open_pull_request_other_github_error(
        self, mock_isfile, mock_github_class, mock_sleep, mock_rate_limit_wait
    ):
        """Test pull request creation with other GitHub errors."""
        # Setup mocks
        mock_isfile.return_value = False

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user

        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        mock_repo = MagicMock()
        mock_org.get_repo.return_value = mock_repo

        # create_pull raises 500 error
        error_data = {"message": "Internal Server Error"}
        mock_repo.create_pull.side_effect = GithubException(500, error_data, {})

        with patch("builtins.print"):
            result = pr.open_pull_request(
                "/path/to/testrepo",
                "main",
                "feature-branch",
                self.args,
                self.config,
            )

        # Should return None but not raise
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
