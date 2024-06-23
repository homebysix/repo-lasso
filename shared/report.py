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

import json
import os
from datetime import datetime

from . import (
    INTVDIR,
    PR_TEMPLATE,
    REPORTDIR,
    __version__,
    colors,
    cprint,
    get_org_repos,
)


def main(args, config):
    """Main function for report verb."""

    cprint("\nREPORT", colors.OKBLUE)

    # Get list of branches based on PR templates saved in the initiatives directory
    if not os.path.isdir(INTVDIR):
        os.mkdir(INTVDIR)
        intv_branches = []
    else:
        intv_branches = [
            os.path.splitext(file)[0]
            for file in os.listdir(INTVDIR)
            if file.endswith(".md")
        ]

    # Create directory to hold reports
    if not os.path.isdir(REPORTDIR):
        os.mkdir(REPORTDIR)

    # Read report data from stored file, if it exists
    report_data = {}
    report_path = os.path.join(REPORTDIR, config["github_org"] + ".json")
    report_md = os.path.join(REPORTDIR, config["github_org"] + ".md")
    if os.path.isfile(report_path):
        with open(report_path, "rb") as infile:
            report_data = json.load(infile)
        # Create files in initiatives directory for each branch in an existing report
        for r_branch in report_data:
            intv_file = os.path.join(INTVDIR, r_branch + ".md")
            if not os.path.isfile(intv_file):
                with open(intv_file, "w", encoding="utf-8") as outfile:
                    outfile.write(PR_TEMPLATE % r_branch)
                intv_branches.append(r_branch)

    # Stop here if no initiatives were found
    if not intv_branches:
        cprint(
            "No initiatives found. Use `./RepoLasso.py branch` to create one.",
            colors.WARNING,
        )
        return
    print(f"Found {len(intv_branches)} initiatives.")

    # Check status of pull requests for each branch
    repos = get_org_repos(config, args)
    try:
        for idx, repo in enumerate(repos):
            print(
                f"Checking PRs for repo {repo.full_name} ({idx + 1} of {len(repos)})..."
            )
            repo_prs = repo.get_pulls(state="all", sort="created")
            for idx, branch in enumerate(intv_branches):
                branch_prs = [
                    x
                    for x in repo_prs
                    if x.user.login == config["github_username"]
                    if x.head.ref == branch
                ]
                if not branch_prs:
                    continue
                print(f"  Found {branch}")
                for branch_pr in branch_prs:
                    pr = {
                        "html_url": branch_pr.html_url,
                        "state": branch_pr.state,
                        "merged": branch_pr.merged,
                        "created_at": str(branch_pr.created_at),
                        "updated_at": str(branch_pr.updated_at),
                        "closed_at": str(branch_pr.closed_at),
                        "merged_at": str(branch_pr.merged_at),
                        "additions": branch_pr.additions,
                        "deletions": branch_pr.deletions,
                        "changed_files": branch_pr.changed_files,
                        "mergeable": branch_pr.mergeable,
                    }

                    # Update report data
                    if branch not in report_data:
                        report_data[branch] = {}
                    if not report_data[branch].get("pull_requests"):
                        report_data[branch]["pull_requests"] = [pr]
                    elif branch_pr.html_url not in [
                        x["html_url"] for x in report_data[branch]["pull_requests"]
                    ]:
                        report_data[branch]["pull_requests"].append(pr)

                # Update report json and markdown after each initiative is processed
                with open(report_path, "w", encoding="utf-8") as outfile:
                    outfile.write(json.dumps(report_data, indent=4))
        cprint(f"Wrote data: {os.path.relpath(report_path)}", colors.OKGREEN)

    except KeyboardInterrupt:
        cprint("Ctrl-C received.", colors.FAIL)

    finally:
        report_data = dict(sorted(report_data.items()))
        # Update markdown
        time_now = datetime.now().astimezone().replace(microsecond=0).isoformat()
        pr_count = sum(len(x["pull_requests"]) for x in report_data.values())
        md_data = f"# RepoLasso report for `{config['github_org']}` org"
        md_data += f"\n\nGenerated {time_now} by [Repo Lasso]"
        md_data += f"(https://github.com/homebysix/repo-lasso) {__version__}."
        md_data += (
            f"\n\nFound {pr_count} pull requests across {len(report_data)} initiatives."
        )
        for branch_name, branch_data in report_data.items():
            md_data += f"\n\n## {branch_name}"
            with open(
                os.path.join(INTVDIR, branch_name + ".md"), encoding="utf-8"
            ) as infile:
                pr_message = infile.read()
            # Decrease all markdown headings by two levels for quoting
            pr_message = pr_message.replace("\n#", "\n###")
            if pr_message.startswith("#"):
                pr_message = "##" + pr_message
            md_data += "\n\n>"
            md_data += "\n> ".join(pr_message.split("\n"))
            md_data += "\n\n| PR  | Created | Status |"
            md_data += "\n| --- | ------- | ------ |"
            for pr in branch_data.get("pull_requests", []):
                if pr["merged"] is True:
                    status = "🟢 merged"
                elif pr["state"] == "closed":
                    status = "🔴 closed"
                elif pr["mergeable"] is False:
                    status = "⛔️ conflict"
                else:
                    status = "🔵 open"
                shortened_pr = (
                    pr["html_url"]
                    .replace("https://github.com/", "")
                    .replace("/pull/", "#")
                )
                md_data += (
                    f"\n| [{shortened_pr}]({pr["html_url"]})"
                    f" | {pr["created_at"]} | {status} |"
                )
            md_data += "\n\n---"

        with open(report_md, "w", encoding="utf-8") as outfile:
            outfile.write(md_data)
        cprint(f"Wrote report: {os.path.relpath(report_md)}", colors.OKGREEN)
