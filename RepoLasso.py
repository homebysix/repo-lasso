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

import sys
from textwrap import dedent
from time import time

from shared import (  # noqa: F401
    CONFIG_PATH,
    LOGO,
    __version__,
    branch,
    build_argument_parser,
    check,
    colors,
    commit,
    cprint,
    get_config,
    pr,
    readable_time,
    report,
    reset,
    status,
    sync,
)


def main() -> None:
    """Main process."""

    start = time()

    # Parse command line arguments.
    argparser = build_argument_parser()
    args = argparser.parse_args()

    if "func" not in args.__dict__:
        # Show help if no verb was provided.
        argparser.print_help()
        sys.exit(0)

    cprint(dedent(LOGO), colors.HEADER)

    # Read configuration or prompt user for configuration items.
    cprint("CONFIGURATION", colors.OKBLUE)
    config = get_config(CONFIG_PATH, args)

    # Kick off desired verb.
    args.func.main(args, config)

    # Print run duration.
    cprint(f"\nFinished in {readable_time(time() - start)}.", colors.HEADER)


if __name__ == "__main__":
    main()
