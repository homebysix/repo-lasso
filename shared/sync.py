#!/usr/bin/env python3

# Copyright 2021-2024 Elliot Jordan
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
import os
import subprocess
import sys
from multiprocessing.pool import ThreadPool
from typing import Any, Dict, Generator, List

from github import Github
from github.GithubException import GithubException

from . import REPODIR, colors, cprint, get_clones, get_default_branch, get_org_repos


def get_user_forks(org_repos: List[Any], config: Dict[str, Any]) -> List[Any]:
    """Return API information about your forks of org repos."""

    # Object for communicating with GitHub API
    g = Github(config["github_token"])

    org_full_names = [x.full_name for x in org_repos]
    user_forks = []
    for repo in g.get_user().get_repos(type="forks"):
        if not repo.fork:
            continue
        if repo.parent.full_name in org_full_names:
            user_forks.append(repo)

    f_noun = "fork" if len(user_forks) == 1 else "forks"
    r_noun = "repo" if len(org_repos) == 1 else "repos"
    print(
        f"{len(user_forks)} {f_noun} of {config['github_org']} "
        f"{r_noun} by user {config['github_username']}."
    )

    return user_forks


def create_user_forks(
    repos_to_fork: List[Any], config: Dict[str, Any]
) -> Generator[Any, None, None]:
    """Create forks for any repos not already forked from org."""

    print(f"Need to create forks for the following {len(repos_to_fork)} repos:")
    print("  - " + "\n  - ".join([x.full_name for x in repos_to_fork]))
    response = input(
        f"OK to create forks in the {config['github_username']} GitHub account? [y/n] "
    )
    if not response.lower().startswith("y"):
        cprint("ERROR: Did not consent to fork repos. Exiting.", colors.FAIL)
        cprint(
            "TIP: You can set the `--excluded-repo` CLI parameter or the "
            "`excluded_repos` key in your config file to ignore specific "
            "repos in an organization. See `--help` for usage information.",
            colors.OKGREEN,
        )
        sys.exit(0)
    for idx, repo in enumerate(repos_to_fork):
        print(f"Forking repo {repo.full_name} ({idx + 1} of {len(repos_to_fork)})...")
        try:
            yield repo.create_fork()
        except GithubException as err:
            cprint(
                f"Attempt to fork repo {repo.full_name} failed. "
                f"Create the fork manually on GitHub, then try again: {repo.html_url}",
                colors.WARNING,
                2,
            )
            cprint(str(err), colors.WARNING, 2)


def create_clones(forks_to_clone: List[Any], config: Dict[str, Any]) -> None:
    """Create clones for any forks not already cloned locally."""

    print(f"Need to create clones for the following {len(forks_to_clone)} repos:")
    print(
        "  - "
        + "\n  - ".join(
            [
                f"{x.full_name} (fork of {config['github_org']}/{x.name})"
                for x in forks_to_clone
            ]
        )
    )
    response = input("OK to create clones? [y/n] ")
    if not response.lower().startswith("y"):
        cprint("ERROR: Did not consent to clone forks. Exiting.", colors.FAIL)
        cprint(
            "TIP: You can set the `--excluded-repo` CLI parameter or the "
            "`excluded_repos` key in your config file to ignore specific "
            "repos in an organization. See `--help` for usage information.",
            colors.OKGREEN,
        )
        sys.exit(0)
    for idx, fork in enumerate(forks_to_clone):
        print(
            f"Cloning fork of {config['github_org']}/{fork.name} "
            f"({idx + 1} of {len(forks_to_clone)})..."
        )
        clone_path = os.path.join(REPODIR, config["github_org"], fork.name)
        clone_cmd = ["git", "clone", "--depth=1", fork.clone_url, clone_path]
        _ = subprocess.run(clone_cmd, check=True, capture_output=True, text=True)
        remote_cmd = [
            "git",
            "-C",
            clone_path,
            "remote",
            "add",
            "upstream",
            fork.parent.clone_url,
        ]
        _ = subprocess.run(remote_cmd, check=True, capture_output=True, text=True)

        # Get the default branch from the upstream repository
        upstream_default_branch = fork.parent.default_branch

        # Fetch only the default branch from upstream to avoid issues with
        # case-insensitive filesystems and conflicting branch names
        fetch_upstream_cmd = [
            "git",
            "-C",
            clone_path,
            "fetch",
            "upstream",
            upstream_default_branch,
        ]
        _ = subprocess.run(
            fetch_upstream_cmd, check=True, capture_output=True, text=True
        )

        # Set upstream HEAD to track the default branch
        set_upstream_head_cmd = [
            "git",
            "-C",
            clone_path,
            "remote",
            "set-head",
            "upstream",
            upstream_default_branch,
        ]
        _ = subprocess.run(
            set_upstream_head_cmd, check=True, capture_output=True, text=True
        )

        # If repo has pre-commit configured, install the hooks
        if os.path.isfile(os.path.join(clone_path, ".pre-commit-config.yaml")):
            try:
                _ = subprocess.run(["pre-commit", "install"], check=False)
            except FileNotFoundError:
                pass


def sync_clone(
    clone: str, config: Dict[str, Any], args: argparse.Namespace, idx: int, total: int
) -> None:
    """Fetch and pull a clone from upstream, and push commits to origin."""

    cprint(
        f"Syncing clone {os.path.relpath(clone)} ({idx} of {total})...",
        colors.OKBLUE,
    )
    # Get the actual default branch for this repository
    default_branch = get_default_branch(clone)
    curr_branch_cmd = ["git", "-C", clone, "branch", "--show-current"]
    proc = subprocess.run(curr_branch_cmd, check=True, capture_output=True, text=True)
    current_branch = proc.stdout.strip()

    fetch_cmd = ["git", "-C", clone, "fetch", "--all"]
    fetch_proc = subprocess.run(
        fetch_cmd, check=False, capture_output=args.verbose == 0
    )
    if fetch_proc.returncode != 0:
        cprint(f"Failed to fetch upstream for {clone}. ", colors.WARNING, 2)
        return
    if current_branch in ("main", "master"):
        pull_cmd = ["git", "-C", clone, "pull", "--ff-only", "upstream", default_branch]
        pull_proc = subprocess.run(
            pull_cmd, check=False, capture_output=args.verbose == 0
        )
        if pull_proc.returncode != 0:
            cprint(f"Failed to pull upstream for {clone}. ", colors.WARNING, 2)
            return
        push_cmd = ["git", "-C", clone, "push", "origin"]
        push_proc = subprocess.run(
            push_cmd, check=False, capture_output=args.verbose == 0
        )
        if push_proc.returncode != 0:
            cprint(f"Failed to push origin for {clone}. ", colors.WARNING, 2)
            return


def parallelize(args: Any) -> Any:
    """Helper function that allows us to compact needed arguments and pass them
    to the sync_clone() function."""

    return sync_clone(*args)


def main(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    """Main function for sync verb."""

    cprint("\nSYNC", colors.OKBLUE)

    print(
        f"Retrieving information about {config['github_org']} org repos "
        "(this should take a few seconds)..."
    )
    repos = get_org_repos(config, args)
    print(f"{len(repos)} eligible repos in {config['github_org']} org.")

    print(
        f"Retrieving information about your forks of the {config['github_org']} org repos "
        "(this may take a bit longer)..."
    )
    forks = get_user_forks(repos, config)
    missing_forks = [
        x for x in repos if x.full_name not in [y.parent.full_name for y in forks]
    ]
    if missing_forks:
        forks.extend(create_user_forks(missing_forks, config))

    clones = get_clones(config)
    missing_clones = [
        x
        for x in forks
        if not os.path.isdir(os.path.join(REPODIR, config["github_org"], x.name))
    ]
    if missing_clones:
        create_clones(missing_clones, config)

    print("Syncing clones (fetch/pull from upstream, push to origin)...")
    # TODO: Offer --serial flag for running syncs one at a time.
    # for idx, clone in enumerate(clones)
    #     sync_clone(clones, config, args, idx + 1, len(clones))
    number_of_workers = 48
    with ThreadPool(number_of_workers) as pool:
        pool.map(
            parallelize,
            [
                (clone, config, args, idx + 1, len(clones))
                for idx, clone in enumerate(clones)
            ],
        )
