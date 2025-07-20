import os
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, mock_open, patch

# Add the parent directory to sys.path to import the shared module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared import pr


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

    @patch("shared.pr.sleep")
    @patch("shared.pr.Github")
    @patch("shared.pr.os.path.isfile")
    def test_open_pull_request_success(
        self, mock_isfile, mock_github_class, mock_sleep
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

    @patch("shared.pr.Github")
    @patch("shared.pr.os.path.isfile")
    @patch("shared.pr.load_pr_template")
    def test_open_pull_request_with_template(
        self, mock_load_template, mock_isfile, mock_github_class
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


if __name__ == "__main__":
    unittest.main()
