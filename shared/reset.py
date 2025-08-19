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
from typing import Any, Dict

from . import colors, cprint, get_clones, get_default_branch


def main(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    """Main function for reset verb."""

    cprint("\nRESET", colors.OKBLUE)

    clones = get_clones(config)
    for idx, clone in enumerate(clones):
        print(f"Resetting {os.path.relpath(clone)} ({idx + 1} of {len(clones)})...")
        try:
            # Get the actual default branch for this repository
            default_branch = get_default_branch(clone)

            # Initial reset on current branch
            reset_cmd = ["git", "-C", clone, "reset", "--hard"]
            subprocess.run(reset_cmd, check=True, capture_output=True, text=True)

            # Checkout default branch
            checkout_cmd = ["git", "-C", clone, "checkout", default_branch]
            subprocess.run(checkout_cmd, check=True, capture_output=True, text=True)

            # Reset again on default branch
            subprocess.run(reset_cmd, check=True, capture_output=True, text=True)

            # Clean untracked files
            clean_cmd = ["git", "-C", clone, "clean", "-xdf"]
            subprocess.run(clean_cmd, check=True, capture_output=True, text=True)

        except subprocess.CalledProcessError as e:
            cprint(f"ERROR: Failed to reset {os.path.relpath(clone)}", colors.FAIL)
            if e.stderr:
                cprint(f"  Git error: {e.stderr.strip()}", colors.FAIL)
            else:
                cprint(f"  Command failed: {' '.join(e.cmd)}", colors.FAIL)
            continue
        except Exception as e:
            cprint(
                f"ERROR: {os.path.relpath(clone)}: {e}",
                colors.FAIL,
            )
            continue
