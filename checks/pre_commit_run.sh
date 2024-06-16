#!/bin/bash

# $1 is the path to the git clone
# $2 is the path to the file being tested
# $3 is the number of the current attempt

cd "$1" && pre-commit run --all-files
