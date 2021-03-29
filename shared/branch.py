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

import os
import subprocess

from . import INTVDIR, colors, cprint, get_branch_info, get_clones, get_index_info


def create_branch(branch_name, config, clones):
    print("Creating branch %s..." % branch_name)
    for idx, clone in enumerate(clones):
        print(
            "Checking out branch %s in clone %s (%d of %d)..."
            % (
                branch_name,
                os.path.relpath(clone),
                idx + 1,
                len(clones),
            )
        )
        branch_cmd = ["git", "-C", clone, "branch"]
        proc = subprocess.run(branch_cmd, check=True, capture_output=True, text=True)
        branches = [x.strip() for x in proc.stdout.replace("*", "").split("\n")]
        if branch_name in branches:
            checkout_cmd = ["git", "-C", clone, "checkout", branch_name]
        else:
            checkout_cmd = ["git", "-C", clone, "checkout", "-b", branch_name]
        _ = subprocess.run(checkout_cmd, check=True, capture_output=True, text=True)

    # Create empty pull request template
    pr_template = os.path.join(INTVDIR, branch_name + ".md")
    if not os.path.isdir(INTVDIR):
        os.mkdir(INTVDIR)
    if not os.path.isfile(pr_template):
        with open(pr_template, "w") as outfile:
            outfile.write(
                "# %s\n\n"
                "Description of changes included in this pull request.\n" % branch_name
            )


def main(args, config):
    """Main function for branch verb."""
    cprint("\nBRANCH", colors.OKBLUE)

    # Make branch ID branch-name-friendly
    branch_name = args.name.replace(" ", "-").replace("/", "-").replace(":", "-")

    # Evaluate branch state of clones
    clones = get_clones(config)
    branches = get_branch_info(clones)
    changes = get_index_info(clones)
    if all((x in ("master", "main") for x in branches)):
        # Create new branch from default branch.
        create_branch(branch_name, config, clones)
    elif list(branches.keys()) == [branch_name] and not changes.get("dirty"):
        # No need to create new branch. Waiting for changes to be made.
        print("All clones are already on the %s branch." % branch_name)
    elif len(branches) == 1 and not changes.get("dirty"):
        # Create new branch from current branch.
        curr_branch = list(branches.keys())[0]
        print("Clones are clean and on the %s branch." % curr_branch)
        # TODO: Compare with default branch to know whether changes exist.
        cprint(
            "WARNING: Additional changes may already exist on the %s branch."
            % curr_branch,
            colors.WARNING,
        )
        create_branch(branch_name, config, clones)
    else:
        cprint("ERROR: Clones are not all on the same branch.", colors.FAIL)
        cprint(
            "TIP: Run `./RepoLasso.py reset` to discard unstaged changes "
            "and reset all clones to the default branch.",
            colors.OKGREEN,
        )
        return

    cprint(
        "Ready for you to make the changes associated with this branch.",
        colors.OKGREEN,
    )
    cprint(
        "Once all changes are complete, run `./RepoLasso.py commit` to commit them.",
        colors.OKGREEN,
    )
