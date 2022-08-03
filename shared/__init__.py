#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2021 Elliot Jordan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import os
import subprocess
from getpass import getpass
from glob import glob
from textwrap import indent

from github import Github, enable_console_debug_logging

__version__ = "1.0.0"

# Path to base directories for storing cloned repositories and initiative info.
REPODIR = os.path.join(os.path.dirname(__file__), "..", "repos")
INTVDIR = os.path.join(os.path.dirname(__file__), "..", "initiatives")

# Path to the configuration file.
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")


def build_argument_parser():
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="output verbosity level (may be specified multiple times)",
    )
    parser.add_argument(
        "--gh-user",
        action="store",
        metavar="USER",
        help="your GitHub username, for creating repository forks",
    )
    parser.add_argument(
        "--gh-token",
        action="store",
        metavar="TOKEN",
        help="a personal access token, for making GitHub API calls",
    )
    parser.add_argument(
        "--gh-org",
        action="store",
        metavar="ORG",
        help="the target GitHub organization to submit changes to",
    )
    parser.add_argument(
        "--exclude-repo",
        action="append",
        metavar="REPO",
        help="repositories to exclude from submitted changes (may be "
        "specified multiple times)",
    )
    subparsers = parser.add_subparsers()

    status_parser = subparsers.add_parser(
        "status",
        help="get branch and clean/dirty status of current cached clones",
    )
    status_parser.set_defaults(func=status)  # noqa: F821

    sync_parser = subparsers.add_parser(
        "sync",
        help="get information about target org repos from the "
        "GitHub API, create forks of all eligible repos, and "
        "clone the forks locally",
    )
    sync_parser.set_defaults(func=sync)  # noqa: F821

    branch_parser = subparsers.add_parser(
        "branch",
        help="create a new branch or switch to an existing branch on all clones",
    )
    branch_parser.add_argument("name", help="branch name")
    branch_parser.set_defaults(func=branch)  # noqa: F821

    check_parser = subparsers.add_parser(
        "check",
        help="check changes on the current branch and store their results",
    )
    check_parser.add_argument("script", help="script used to check changes")
    check_parser.add_argument(
        "--tries", default=1, help="number of times to try script per check"
    )
    check_parser.add_argument(
        "--revert", action="store_true", help="revert changes if checks fail"
    )
    check_parser.set_defaults(func=check)  # noqa: F821

    commit_parser = subparsers.add_parser(
        "commit",
        help="create a new commit on the current branch across all clones",
    )
    commit_parser.add_argument("message", help="commit message")
    commit_parser.set_defaults(func=commit)  # noqa: F821

    pr_parser = subparsers.add_parser(
        "pr",
        help="push new commits to the origin and open pull requests for any "
        "clones with changes",
    )
    pr_parser.set_defaults(func=pr)  # noqa: F821
    pr_parser.add_argument(
        "--template",
        action="store",
        help="path to a markdown template to use for pull requests",
    )

    reset_parser = subparsers.add_parser(
        "reset",
        help="discard unstaged changes to all repos, check out "
        "default branch, and fetch/pull latest changes from "
        "GitHub in preparation for creating a new initiative",
    )
    reset_parser.set_defaults(func=reset)  # noqa: F821

    report_parser = subparsers.add_parser(
        "report",
        help="report on the status of previous initiatives, "
        "including whether submitted pull requests have been "
        "merged",
    )
    report_parser.set_defaults(func=report)  # noqa: F821

    return parser


class colors:
    """Colors to use when displaying output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"


def cprint(msg, color_class, indent_level=0):
    """Function for printing colorized output."""

    print(indent(f"{color_class}{msg}{colors.ENDC}", " " * indent_level))


def get_config(path, args):
    """Read existing configuration or prompt user to create a new one."""
    if os.path.isfile(path):
        print("Reading configuration from %s..." % os.path.relpath(path))
        try:
            with open(path, "rb") as infile:
                config = json.load(infile)
        except json.decoder.JSONDecodeError:
            print("WARNING: Unable to read configuration.", colors.WARNING)
            config = {}
    else:
        print("Creating new config file at %s..." % os.path.relpath(path))
        config = {}

    # Set GitHub username
    if args.gh_user:
        print("GitHub username (from CLI): %s" % args.gh_user)
        config["github_username"] = args.gh_user
    elif config.get("github_username"):
        print("GitHub username (from config): %s" % config["github_username"])
    else:
        config["github_username"] = input("Enter GitHub username: ")

    # Check for stored GitHub tokens
    autopkg_token = os.path.expanduser("~/.autopkg_gh_token")
    if args.gh_token:
        print("GitHub token (from CLI): <stored>")
        config["github_token"] = args.gh_token
    elif config.get("github_token"):
        print("GitHub token (from config): <stored>")
    elif os.path.isfile(autopkg_token):
        print("A GitHub personal access token was found at %s" % autopkg_token)
        response = input("Do you want to use this token? [y/n] ")
        if response.lower().startswith("y"):
            with open(autopkg_token, "r") as infile:
                config["github_token"] = infile.read().strip()
    # If no stored GitHub tokens, prompt for one
    if not config.get("github_token"):
        github_token = getpass("Enter GitHub personal access token: ")
        config["github_token"] = github_token

    # Set GitHub org
    if args.gh_org:
        print("GitHub org (from CLI): %s" % args.gh_org)
        config["github_org"] = args.gh_org
    elif config.get("github_org"):
        print("GitHub org (from config): %s" % config["github_org"])
    else:
        config["github_org"] = input("Enter GitHub org: ")

    # Create folder for GitHub org, if none exists
    if not os.path.isdir(REPODIR):
        os.mkdir(REPODIR)
    if not os.path.isdir(os.path.join(REPODIR, config["github_org"])):
        os.mkdir(os.path.join(REPODIR, config["github_org"]))

    # Set excluded repos
    if args.exclude_repo:
        excluded_repos = [
            trim_leading_org(x, config["github_org"]) for x in args.exclude_repo
        ]
        print("Excluded repos (from CLI): %s" % excluded_repos)
        config["excluded_repos"] = excluded_repos
    elif config.get("excluded_repos"):
        excluded_repos = [
            trim_leading_org(x, config["github_org"]) for x in config["excluded_repos"]
        ]
        print("Excluded repos (from config): %s" % config["excluded_repos"])

    # Save updated config
    with open(path, "w") as outfile:
        outfile.write(json.dumps(config, indent=4))

    return config


def readable_time(seconds):
    """Converts a number of seconds to a human-readable time in seconds, minutes, and hours."""

    parts = []
    if seconds >= 86400:  # 1 day
        days = seconds // 86400
        if days == 1:
            parts.append("{} day".format(int(days)))
        else:
            parts.append("{} days".format(int(days)))
    if seconds >= 3600:  # 1 hour
        hours = seconds // 3600 % 24
        if hours == 1:
            parts.append("{} hour".format(int(hours)))
        else:
            parts.append("{} hours".format(int(hours)))
    if seconds >= 60:  # 1 hour
        minutes = seconds // 60 % 60
        if minutes == 1:
            parts.append("{} minute".format(int(minutes)))
        else:
            parts.append("{} minutes".format(int(minutes)))
    seconds = round(seconds % 60, 2)
    if seconds == 1:
        parts.append("{} second".format(seconds))
    else:
        parts.append("{} seconds".format(seconds))

    return ", ".join(parts)


def trim_leading_org(repo, org):
    """Strips leading organization from repository names.
    Example: autopkg/recipes --> recipes
    """
    if repo.startswith(org + "/"):
        return repo.replace(org + "/", "")
    return repo


def get_org_repos(config, args):
    """Return API information about org repos."""

    # Object for communicating with GitHub API
    g = Github(config["github_token"])
    if args.verbose >= 2:
        enable_console_debug_logging()

    org_repos = g.get_organization(config["github_org"]).get_repos(type="sources")
    org_repos
    if org_repos.totalCount > 99:
        cprint(
            "WARNING: There are %d repositories in this organization. "
            "This may take a while." % org_repos.totalCount,
            colors.WARNING,
        )
    repos = []
    for repo in org_repos:
        # Skip excluded, archived, private, or empty repos.
        if repo.name in config.get("excluded_repos", []):
            if args.verbose >= 1:
                print("Skipping %s (excluded)..." % repo.full_name)
            continue
        if repo.archived:
            if args.verbose >= 1:
                print("Skipping %s (archived)..." % repo.full_name)
            continue
        if repo.private:
            if args.verbose >= 1:
                print("Skipping %s (private)..." % repo.full_name)
            continue
        # if repo.size == 0:
        #     if args.verbose >= 1:
        #         print("Skipping %s (empty)..." % repo.full_name)
        #     continue
        repos.append(repo)

    return repos


def get_clones(config):
    """Get information on clones in the cache."""

    clones = glob(os.path.join(REPODIR, config["github_org"], "*"))
    clones = [x for x in clones if os.path.isdir(os.path.join(x, ".git"))]
    noun = "clone" if len(clones) == 1 else "clones"
    verb = "is" if len(clones) == 1 else "are"
    print("%d repo %s %s cached." % (len(clones), noun, verb))
    if not clones:
        cprint(
            "TIP: Run `./RepoLasso.py sync` to fork and clone repos "
            "in the %s org." % config["github_org"],
            colors.OKGREEN,
        )

    return clones


def get_branch_info(clones):
    """Get information on which clones are on which branches."""

    branch_info = {}
    for clone in clones:
        branch_cmd = ["git", "-C", clone, "branch", "--show-current"]
        proc = subprocess.run(branch_cmd, check=False, capture_output=True, text=True)
        branch = proc.stdout.strip()
        if branch in branch_info:
            branch_info[branch].append(clone)
        else:
            branch_info[branch] = [clone]

    return branch_info


def get_index_info(clones):
    """Get information on which clones are dirty or clean."""

    index_info = {"clean": [], "dirty": []}
    for clone in clones:
        index_cmd = ["git", "-C", clone, "status", "--short"]
        proc = subprocess.run(index_cmd, check=False, capture_output=True, text=True)
        changes = proc.stdout.strip()
        if changes:
            index_info["dirty"].append(clone)
        else:
            index_info["clean"].append(clone)

    return index_info
