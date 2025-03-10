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

import os
import subprocess
import sys
from multiprocessing.pool import ThreadPool

from github import Github
from github.GithubException import GithubException

from . import REPODIR, colors, cprint, get_clones, get_org_repos


def get_user_forks(org_repos, config):
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


def create_user_forks(repos_to_fork, config):
    """Create forks for any repos not already forked from org."""

    print(f"Need to create forks for the following {len(repos_to_fork)} repos:")
    print("  - " + "\n  - ".join([x.full_name for x in repos_to_fork]))
    response = input(
        f"OK to create forks in the {config['github_username']} GitHub account? [y/n] "
    )
    if not response.lower().startswith("y"):
        cprint("Did not consent to fork repos. Exiting.", colors.WARNING)
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
            cprint(err, colors.WARNING, 2)


def create_clones(forks_to_clone, config):
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
        cprint("Did not consent to clone forks. Exiting.", colors.WARNING)
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
        clone_cmd = ["git", "clone", "--depth=1", fork.ssh_url, clone_path]
        _ = subprocess.run(clone_cmd, check=True, capture_output=True, text=True)
        remote_cmd = [
            "git",
            "-C",
            clone_path,
            "remote",
            "add",
            "upstream",
            fork.parent.ssh_url,
        ]
        _ = subprocess.run(remote_cmd, check=True, capture_output=True, text=True)

        # If repo has pre-commit configured, install the hooks
        if os.path.isfile(os.path.join(clone_path, ".pre-commit-config.yaml")):
            try:
                _ = subprocess.run(["pre-commit", "install"], check=False)
            except FileNotFoundError:
                pass


def sync_clone(clone, config, args, idx, total):
    """Fetch and pull a clone from upstream, and push commits to origin."""

    cprint(
        f"Syncing clone {os.path.relpath(clone)} ({idx} of {total})...",
        colors.OKBLUE,
    )
    # TODO: Determine this based on GitHub API.
    branches_cmd = ["git", "-C", clone, "branch"]
    proc = subprocess.run(branches_cmd, check=True, capture_output=True, text=True)
    branches = [x.strip() for x in proc.stdout.replace("*", "").split("\n")]
    default_branch = "main" if "main" in branches else "master"
    curr_branch_cmd = ["git", "-C", clone, "branch", "--show-current"]
    proc = subprocess.run(curr_branch_cmd, check=True, capture_output=True, text=True)
    current_branch = proc.stdout.strip()

    fetch_cmd = ["git", "-C", clone, "fetch", "--all"]
    _ = subprocess.run(fetch_cmd, check=True, capture_output=args.verbose == 0)
    if current_branch in ("main", "master"):
        pull_cmd = ["git", "-C", clone, "pull", "--ff-only", "upstream", default_branch]
        _ = subprocess.run(pull_cmd, check=True, capture_output=args.verbose == 0)
        push_cmd = ["git", "-C", clone, "push", "origin"]
        _ = subprocess.run(push_cmd, check=True, capture_output=args.verbose == 0)


def parallelize(args):
    """Helper function that allows us to compact needed arguments and pass them
    to the sync_clone() function."""

    return sync_clone(*args)


def main(args, config):
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
