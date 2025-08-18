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
import sys
from multiprocessing.pool import ThreadPool
from typing import Any, Dict, Optional

from . import INTVDIR, colors, cprint, get_clones


def summarize(results: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
    """Print summary of check results."""
    c_err = 0
    f_err = 0
    for clone, c_results in results.items():
        printed_clone = False
        for filepath, f_results in c_results.items():
            if f_results["before"] != f_results["after"]:
                if not printed_clone:
                    print(clone)
                    printed_clone = True
                    c_err += 1
                print(f"  {clone}/{filepath}")
                cprint(
                    f"    Exit codes before: {f_results['before']}"
                    f" / Exit codes after: {f_results['after']}",
                    colors.WARNING,
                )
                f_err += 1

    print(f"\n{f_err} files failed checks across {c_err} clones.")


def check_repo(
    clone: str, args: argparse.Namespace, idx: int, total: int
) -> Optional[Dict[str, Dict[str, Dict[str, Any]]]]:
    """Checks a single repository."""

    clone = os.path.relpath(clone)
    print(f"Looking for changes in clone {clone} ({idx + 1} of {total} repos)...")

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
        return None

    c_files = [x[2:].strip() for x in proc.stdout.strip().split("\n")]
    result: Dict[str, Dict[str, Any]] = {}

    for fidx, c_file in enumerate(c_files):
        print(f"Checking {c_file} ({fidx + 1} of {len(c_files)} files in {clone})...")

        # Test on current git HEAD, without uncommitted changes
        stash_cmd = ["git", "-C", clone, "stash"]
        proc = subprocess.run(stash_cmd, check=True, capture_output=True, text=True)
        checks_before = []
        for i in range(0, int(args.tries)):
            proc = subprocess.run(
                [args.script, os.path.relpath(clone), c_file, str(i)],
                check=False,
                capture_output=True,
                text=True,
            )
            checks_before.append(proc.returncode)

        # Reapply changes and test again
        stash_cmd = ["git", "-C", clone, "stash", "pop"]
        proc = subprocess.run(stash_cmd, check=True, capture_output=True, text=True)
        checks_after = []
        for i in range(0, int(args.tries)):
            proc = subprocess.run(
                [args.script, os.path.relpath(clone), c_file, str(i)],
                check=False,
                capture_output=True,
                text=True,
            )
            checks_after.append(proc.returncode)

        # Save return codes)
        result[c_file] = {"before": checks_before, "after": checks_after}
        if checks_before != checks_after:
            cprint(
                f"{args.script} return codes differ before/after changes for file {clone}/{c_file}",
                colors.WARNING,
            )
            if args.revert:
                # Revert changes to this file
                revert_cmd = ["git", "-C", clone, "checkout", c_file]
                proc = subprocess.run(revert_cmd, check=False, text=True)

    return {clone: result}


def parallelize(args: Any) -> Optional[Dict[str, Dict[str, Dict[str, Any]]]]:
    """Helper function that allows us to compact needed arguments and pass them
    to the check_repo() function."""

    return check_repo(*args)


def main(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    """Main function for check verb."""
    cprint("\nCHECK", colors.OKBLUE)

    if not os.path.isfile(args.script):
        cprint(f"The check script does not exist: {args.script}", colors.FAIL)
        sys.exit(1)

    try:
        int(args.tries)
    except ValueError:
        cprint(f"Number of tries must be an integer: {args.script}", colors.FAIL)
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
    #     exit(0)

    clones = get_clones(config)
    results: Dict[str, Dict[str, Dict[str, Any]]] = {}

    # Trap Control-C and display summary before exit.
    try:
        number_of_workers = os.cpu_count()
        with ThreadPool(number_of_workers) as pool:
            result_list = pool.map(
                parallelize,
                [(clone, args, idx, len(clones)) for idx, clone in enumerate(clones)],
            )
        results = {}
        for result in result_list:
            if result is None:
                continue
            for clone, c_results in result.items():
                if clone not in results:
                    results[clone] = {}
                for filepath, f_results in c_results.items():
                    results[clone][filepath] = f_results
    finally:
        with open(results_file, "w", encoding="utf-8") as openfile:
            openfile.write(json.dumps(results, indent=4))
        summarize(results)
