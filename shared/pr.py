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
import json
import os
import subprocess
from datetime import datetime
from time import sleep
from typing import Any, Dict, Optional, Tuple

from github import Github, GithubException

from . import (
    INTVDIR,
    colors,
    cprint,
    get_clones,
    get_default_branch,
    github_rate_limit_wait,
)


def load_pr_template(template_path: str) -> Tuple[str, str]:
    """Given a path to a markdown file, load the file as a pull request template."""

    with open(template_path, encoding="utf-8") as infile:
        template_contents = infile.read()
    if template_contents.startswith("# "):
        title = template_contents.split("\n")[0].lstrip("# ").strip()
        body = "\n".join(template_contents.split("\n")[1:]).strip()

    return title, body


def open_pull_request(
    clone: str, base: str, head: str, args: argparse.Namespace, config: Dict[str, Any]
) -> Optional[Any]:
    """For an eligible repo, open a pull request on GitHub."""

    # Object for communicating with GitHub API
    g = Github(config["github_token"])

    # Load in PR template, if provided.
    default_pr_template = os.path.join(INTVDIR, head + ".md")
    if args.template and os.path.isfile(args.template):
        print("  Loaded template from CLI options.")
        title, body = load_pr_template(args.template)
    elif os.path.isfile(default_pr_template):
        print("  Loaded template from default path.")
        title, body = load_pr_template(default_pr_template)
    else:
        print("  No template found.")
        title = head
        body = ""

    org = g.get_organization(config["github_org"])
    upstream_repo = org.get_repo(os.path.split(clone)[1])
    try:
        github_rate_limit_wait(config)

        pr = upstream_repo.create_pull(
            base=base,
            head=f"{g.get_user().login}:{head}",
            title=title,
            body=body,
        )
        cprint(f"Pull request opened: {pr.html_url}", colors.OKGREEN, 2)
        # Proactively avoid rate limiting
        sleep(3)
    except GithubException as err:
        if err.status == 422:
            cprint(
                "WARNING: A pull request may already exist for this branch. Skipping.",
                colors.WARNING,
                2,
            )
        else:
            cprint(
                f"WARNING: Unable to open pull request. Details: {err.status} - {err.data}",
                colors.WARNING,
                2,
            )
        pr = None

    return pr


def log_initiative(pr: Any, branch: str, config: Dict[str, Any]) -> None:
    """Update the json file that tracks each initiative."""

    if not os.path.isdir(INTVDIR):
        os.mkdir(INTVDIR)

    intv_path = os.path.join(INTVDIR, config["github_org"] + ".json")
    intv_data = {}
    if os.path.isfile(intv_path):
        with open(intv_path, "rb") as infile:
            intv_data = json.load(infile)
    if branch in intv_data:
        if pr.html_url not in intv_data[branch]["pull_requests"]:
            intv_data[branch]["pull_requests"].append(pr.html_url)
    else:
        intv_data = {
            branch: {
                "created_date": datetime.now()
                .astimezone()
                .replace(microsecond=0)
                .isoformat(),
                "pull_requests": [pr.html_url],
            }
        }
    with open(intv_path, "w", encoding="utf-8") as outfile:
        outfile.write(json.dumps(intv_data, indent=4))


def main(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    """Main function for pr verb."""

    cprint("\nPULL REQUESTS", colors.OKBLUE)
    clones = get_clones(config)
    for idx, clone in enumerate(clones):
        print(
            "Evaluating pull request eligibility for "
            f"{os.path.relpath(clone)} ({idx + 1} of {len(clones)})..."
        )

        # Get the actual default branch for this repository
        default_branch = get_default_branch(clone)

        curr_branch_cmd = ["git", "-C", clone, "branch", "--show-current"]
        proc = subprocess.run(
            curr_branch_cmd, check=True, capture_output=True, text=True
        )
        current_branch = proc.stdout.strip()

        status_cmd = [
            "git",
            "-C",
            clone,
            "log",
            f"{default_branch}..{current_branch}",
            "--oneline",
        ]
        proc = subprocess.run(status_cmd, check=True, capture_output=True, text=True)
        if not proc.stdout:
            continue

        print("  Pushing origin...")
        push_cmd = ["git", "-C", clone, "push", "origin", current_branch]
        _ = subprocess.run(push_cmd, check=True, capture_output=True, text=True)

        print("  Opening pull request...")
        pr = open_pull_request(clone, default_branch, current_branch, args, config)
        if pr:
            log_initiative(pr, current_branch, config)
