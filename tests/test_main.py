import os
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to import RepoLasso
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import RepoLasso


class TestRepoLasso(unittest.TestCase):
    """Test class for main RepoLasso module."""

    @patch("RepoLasso.get_config")
    @patch("RepoLasso.build_argument_parser")
    @patch("RepoLasso.cprint")
    def test_main_with_valid_args(self, mock_cprint, mock_parser, mock_config):
        """Test main function with valid arguments."""
        # Setup mocks
        mock_func = MagicMock()
        mock_func.main = MagicMock()
        mock_args = Namespace(func=mock_func)

        mock_argparser = MagicMock()
        mock_argparser.parse_args.return_value = mock_args
        mock_parser.return_value = mock_argparser

        mock_config.return_value = {"test": "config"}

        # Test
        with patch("sys.argv", ["RepoLasso.py", "sync"]):
            RepoLasso.main()

        # Assertions
        mock_parser.assert_called_once()
        mock_argparser.parse_args.assert_called_once()
        mock_func.main.assert_called_once_with(mock_args, {"test": "config"})

    @patch("RepoLasso.get_config")
    @patch("RepoLasso.build_argument_parser")
    @patch("RepoLasso.cprint")
    def test_main_without_func_shows_help(self, mock_cprint, mock_parser, mock_config):
        """Test main function shows help when no verb is provided."""

        # Create a simple object with empty __dict__ (no func attribute)
        class MockArgs:
            def __init__(self):
                pass

        mock_args = MockArgs()

        mock_argparser = MagicMock()
        mock_argparser.parse_args.return_value = mock_args
        mock_parser.return_value = mock_argparser
        mock_config.return_value = {"test": "config"}

        # Test
        with patch("sys.argv", ["RepoLasso.py"]):
            with patch("sys.exit") as mock_exit:
                RepoLasso.main()

        # Assertions
        mock_argparser.print_help.assert_called_once()
        mock_exit.assert_called_once_with(0)
        # get_config should not be called when no func is present
        mock_config.assert_not_called()
        # cprint should only be called once for the logo, not for CONFIGURATION
        self.assertEqual(mock_cprint.call_count, 1)


if __name__ == "__main__":
    unittest.main()
