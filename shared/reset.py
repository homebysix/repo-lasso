#!/usr/bin/env python3

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

from . import colors, cprint, get_clones


def main(args, config):
    """Main function for reset verb."""

    cprint("\nSTATUS", colors.OKBLUE)

    clones = get_clones(config)
    for idx, clone in enumerate(clones):
        print(f"Resetting {os.path.relpath(clone)} ({idx + 1} of {len(clones)})...")
        # TODO: Determine this based on GitHub API.
        branches_cmd = ["git", "-C", clone, "branch"]
        proc = subprocess.run(branches_cmd, check=True, capture_output=True, text=True)
        branches = [x.strip() for x in proc.stdout.replace("*", "").split("\n")]
        default_branch = "main" if "main" in branches else "master"
        reset_cmd = ["git", "-C", clone, "reset", "--hard"]
        _ = subprocess.run(reset_cmd, check=True, capture_output=True, text=True)
        checkout_cmd = ["git", "-C", clone, "checkout", default_branch]
        _ = subprocess.run(checkout_cmd, check=True, capture_output=True, text=True)
        _ = subprocess.run(reset_cmd, check=True, capture_output=True, text=True)
        clean_cmd = ["git", "-C", clone, "clean", "-xdf"]
        _ = subprocess.run(clean_cmd, check=True, capture_output=True, text=True)
