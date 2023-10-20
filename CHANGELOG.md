# Repo Lasso Change Log

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](http://semver.org/).

<!-- markdownlint-disable MD024 -->

## Unreleased

### Added

- New `check` verb that runs a script of your choosing on changed files in all repos, optionally reverting the changes if the script exits non-zero.
- Sync operations now happen in parallel, making the process much faster.
- Provide hint about the `--excluded-repo` option if fork/clone consent not provided for new repos.

### Changed

- More specific error output when pull requests fail.
- Using `packaging.version.Version` instead of the beloved `distutils.version.LooseVersion` for checking of Recipe Robot beta status.

## 1.0.0 - 2021-03-29

- Initial public release of Repo Lasso.
