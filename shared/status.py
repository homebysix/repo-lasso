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

from . import colors, cprint, get_branch_info, get_clones, get_index_info


def main(args, config):
    """Main function for status verb."""

    cprint("\nSTATUS", colors.OKBLUE)

    # Indented bullet used for lists
    bullet = "  - "

    clones = get_clones(config)
    if not clones:
        return

    print("Checking clone branch status...")
    branches = get_branch_info(clones)
    if all((x in ("master", "main") for x in branches)):
        cprint("All clones are on the default branch.", colors.OKBLUE)
    elif len(branches) == 1:
        cprint(
            "All clones are on the %s branch." % list(branches.keys())[0], colors.OKBLUE
        )
    else:
        cprint("WARNING: Clones are not all on the same branch.", colors.WARNING)
        for branch in branches:
            print(
                "These %d repos are on the %s branch:" % (len(branches[branch]), branch)
            )
            for repo in branches[branch]:
                print(bullet + os.path.relpath(repo))
        cprint(
            "TIP: Run `./RepoLasso.py reset` to discard unstaged changes and "
            "reset all clones to the default branch.",
            colors.OKGREEN,
        )

    print("Checking for uncomitted changes on clones...")
    changes = get_index_info(clones)
    if not changes.get("dirty"):
        cprint("All clones are clean.", colors.OKBLUE)
    else:
        cprint("WARNING: Some clones have uncommitted changes.", colors.WARNING)
        print("These %d repos have uncommitted changes:" % len(changes["dirty"]))
        for repo in changes["dirty"]:
            print(bullet + os.path.relpath(repo))
