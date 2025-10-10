# Repo Lasso Change Log

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](http://semver.org/).

<!-- markdownlint-disable MD024 -->

## [Unreleased]

### Fixed

- More graceful handling of Git fetch, pull, and push errors.
- Greatly improved unit test coverage.
- Better determination of default branch names.

### Changed

- Changed from https to ssh for cloning operations.
- Only fetch default branches on sync, to avoid issues with case-sensitive branch names.
- Python function typing to help Repo Lasso developers and contributors.

## [1.2.0] - 2024-06-23

### Fixed

- Completely rebuilt `report` feature, which is now much more performant and includes the pull request template of each initiative for better context. The backend of this feature stores pull request status in a JSON file that can also be parsed with other tools for those who wish to create their own custom reports.

### Added

- Running `--help` now produces a summary description of Repo Lasso along with a typical workflow diagram.

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

[Unreleased]: https://github.com/homebysix/repo-lasso/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/homebysix/repo-lasso/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/homebysix/repo-lasso/compare/v1.0.0...v1.1.0
