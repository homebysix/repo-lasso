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
    """Main function for commit verb."""
    cprint("\nCOMMIT", colors.OKBLUE)

    clones = get_clones(config)
    for idx, clone in enumerate(clones):
        print(
            "Adding and committing in clone %s (%d of %d)..."
            % (
                os.path.relpath(clone),
                idx + 1,
                len(clones),
            )
        )
        add_cmd = ["git", "-C", clone, "add", "--all"]
        _ = subprocess.run(add_cmd, check=False, capture_output=True)
        commit_cmd = ["git", "-C", clone, "commit", "--message", args.message]
        _ = subprocess.run(commit_cmd, check=False, capture_output=True)
