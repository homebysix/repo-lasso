#!/bin/bash

# $1 is the path to the git clone
# $2 is the path to the file being tested
# $3 is the number of the current attempt (starting with 0)

CACHE_DIR="/tmp/repo-lasso/autopkg-cache"

if [[ $3 -eq 0 ]]; then
    # Clear cache before first attempt of each check
    rm -rf "$CACHE_DIR"
fi

if [[ $2 =~ \.download\.recipe ]]; then
    # Allow download recipes to run
    autopkg run --quiet --key CACHE_DIR="$CACHE_DIR" "${1}/${2}"
elif [[ $2 =~ \.pkg\.recipe ]]; then
    # Allow pkg recipes to run
    autopkg run --quiet --key CACHE_DIR="$CACHE_DIR" "${1}/${2}"
else
    # Limit other recipes to check-only
    autopkg run --quiet --key CACHE_DIR="$CACHE_DIR" --check-only "${1}/${2}"
fi
