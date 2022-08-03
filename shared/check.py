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
import subprocess
import sys

from . import INTVDIR, colors, cprint, get_clones


def summarize(checks):
    """Print summary of check results."""
    c_err = 0
    f_err = 0
    for clone, c_results in checks.items():
        printed_clone = False
        for filepath, f_results in c_results.items():
            if f_results[0] != f_results[1]:
                if not printed_clone:
                    print(clone)
                    printed_clone = True
                    c_err += 1
                print("  %s/%s" % (clone, filepath))
                cprint(
                    "    Exit codes before: %s / Exit codes after: %s"
                    % (f_results[0], f_results[1]),
                    colors.WARNING,
                )
                f_err += 1

    print("\n%d files failed checks across %d clones." % (f_err, c_err))


def main(args, config):
    """Main function for check verb."""
    cprint("\nCHECK", colors.OKBLUE)

    if not os.path.isfile(args.script):
        cprint("The check script does not exist: %s" % args.script, colors.FAIL)
        sys.exit(1)

    try:
        tries = int(args.tries)
    except:
        cprint("Number of tries must be an integer: %s" % args.script, colors.FAIL)
        sys.exit(1)

    # Create JSON file for storing check results.
    results_file = os.path.join(INTVDIR, "checks.json")
    if not os.path.isdir(INTVDIR):
        os.mkdir(INTVDIR)

    # DEBUG
    # if os.path.isfile(results_file):
    #     with open(results_file, "rb") as openfile:
    #         checks = json.load(openfile)
    #     summarize(checks)
    # exit(0)

    clones = get_clones(config)
    checks = {}
    for idx, clone in enumerate(clones):
        clone = os.path.relpath(clone)
        print(
            "Looking for changes in clone %s (%d of %d)..."
            % (clone, idx + 1, len(clones))
        )

        # Skip to next clone if no changes on this branch
        status_cmd = [
            "git",
            "-C",
            clone,
            "status",
            "--short",
            "--porcelain",
        ]
        proc = subprocess.run(status_cmd, check=True, capture_output=True, text=True)
        if not proc.stdout:
            continue

        c_files = [x[2:].strip() for x in proc.stdout.strip().split("\n")]
        checks[clone] = {}

        # Trap Control-C and display summary before exit.
        try:
            for fidx, c_file in enumerate(c_files):
                print(
                    "Checking changed file %s (%d of %d)..."
                    % (c_file, fidx + 1, len(c_files))
                )

                # Test on current git HEAD, without uncommitted changes
                stash_cmd = ["git", "-C", clone, "stash"]
                proc = subprocess.run(
                    stash_cmd, check=True, capture_output=True, text=True
                )
                checks_before = []
                for i in range(0, tries):
                    proc = subprocess.run(
                        [args.script, os.path.relpath(clone), c_file, str(i)],
                        check=False,
                        capture_output=True,
                    )
                    checks_before.append(proc.returncode)

                # Reapply changes and test again
                stash_cmd = ["git", "-C", clone, "stash", "pop"]
                proc = subprocess.run(
                    stash_cmd, check=True, capture_output=True, text=True
                )
                checks_after = []
                for i in range(0, tries):
                    proc = subprocess.run(
                        [args.script, os.path.relpath(clone), c_file, str(i)],
                        check=False,
                        capture_output=True,
                    )
                    checks_after.append(proc.returncode)

                # Save return codes
                checks[clone][c_file] = (checks_before, checks_after)
                if checks_before != checks_after:
                    cprint(
                        "%s return codes differ before/after changes for file %s/%s"
                        % (args.script, clone, c_file),
                        colors.WARNING,
                    )
                with open(results_file, "w") as openfile:
                    openfile.write(json.dumps(checks, indent=4))
        except KeyboardInterrupt:
            summarize(checks)
            sys.exit(0)

    summarize(checks)
