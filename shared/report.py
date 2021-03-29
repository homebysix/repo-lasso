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

import json
import os
from datetime import datetime

from . import INTVDIR, colors, cprint, get_org_repos


def main(args, config):
    """Main function for report verb."""

    cprint("\nREPORT", colors.OKBLUE)

    if not os.path.isdir(INTVDIR):
        os.mkdir(INTVDIR)

    # Read initiative data from stored file, if it exists.
    intv_data = {}
    intv_path = os.path.join(INTVDIR, config["github_org"] + ".json")
    intv_md = os.path.join(INTVDIR, config["github_org"] + ".md")
    if os.path.isfile(intv_path):
        with open(intv_path, "rb") as infile:
            intv_data = json.load(infile)

    md_data = "# RepoLasso Report"
    md_data += (
        "\n\nGenerated: %s"
        % datetime.now().astimezone().replace(microsecond=0).isoformat()
    )
    repos = get_org_repos(config, args)
    for idx, intv_branch in enumerate(intv_data):
        cprint(
            "Checking PRs related to %s (%d of %d)..."
            % (intv_branch, idx + 1, len(intv_data)),
            colors.OKBLUE,
        )
        md_data += "\n\n## %s" % intv_branch
        md_data += "\n\n| PR  | Created | Status |"
        md_data += "\n| --- | ------- | ------ |"
        prs = {}
        for idx, repo in enumerate(repos):
            print(
                "Checking PRs for repo %s (%d of %d)..."
                % (repo.full_name, idx + 1, len(repos))
            )
            repo_prs = repo.get_pulls(
                state="all",
                sort="created",
                head="%s:%s" % (config["github_username"], intv_branch),
            )
            for repo_pr in repo_prs:
                prs[repo_pr.html_url] = {
                    "state": repo_pr.state,
                    "merged": repo_pr.merged,
                    "created_at": str(repo_pr.created_at),
                    "updated_at": str(repo_pr.updated_at),
                    "closed_at": str(repo_pr.closed_at),
                    "merged_at": str(repo_pr.merged_at),
                    "additions": repo_pr.additions,
                    "deletions": repo_pr.deletions,
                    "changed_files": repo_pr.changed_files,
                    "mergeable": repo_pr.mergeable,
                }
                intv_data[intv_branch]["pull_requests"] = prs
                if repo_pr.merged:
                    status = "🟢 merged"
                elif repo_pr.state == "closed":
                    status = "🔴 closed"
                elif not repo_pr.mergeable:
                    status = "⛔️ conflict"
                else:
                    status = "🔵 open"
                md_data += "\n| [%s#%s](%s) | %s | %s |" % (
                    repo.full_name,
                    repo_pr.number,
                    repo_pr.html_url,
                    repo_pr.created_at,
                    status,
                )
                with open(intv_path, "w") as outfile:
                    outfile.write(json.dumps(intv_data, indent=4))
                with open(intv_md, "w") as outfile:
                    outfile.write(md_data)
