# Repo Lasso Change Log

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](http://semver.org/).

<!-- markdownlint-disable MD024 -->

## [Unreleased]

Nothing yet.

## [1.1.0] - 2024-06-16

### Added

- New `check` verb that runs a script of your choosing on changed files in all repos, optionally reverting the changes if the script exits non-zero.
- Sync operations now happen in parallel, making the process much faster.
- Started creating unit tests for Repo Lasso internal functions.
- Provide hint about the `--excluded-repo` option if fork/clone consent not provided for new repos.
- Try to slow down pull request creation if GitHub rate limiting is detected.
- Link to Repo Lasso and version number now included in pull request template.

### Changed

- More specific error output when pull requests fail.
- Various Python upgrades, linting fixes, and standardizations for long term maintainability.

## 1.0.0 - 2021-03-29

- Initial public release of Repo Lasso.

[Unreleased]: https://github.com/homebysix/repo-lasso/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/homebysix/repo-lasso/compare/v1.0.0...v1.1.0
