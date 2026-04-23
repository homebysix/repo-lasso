# Releasing Repo Lasso

Releases are automated via two GitHub Actions workflows in `.github/workflows/`:

- **`release-prep.yml`** — opens a PR that bumps the version and promotes the
  `[Unreleased]` changelog section.
- **`release.yml`** — runs tests and publishes the GitHub release when a
  `vX.Y.Z` tag is pushed.

The shared helper `release_tools.py` implements the version/changelog logic
used by both workflows.

## Cutting a release

1. **Make sure `[Unreleased]` is up to date.** Every PR merged into `dev`
   since the last release should be reflected there. The prep workflow
   refuses to run if the section is empty or says "Nothing yet."

2. **Run the prep workflow.**

   - Go to **Actions → Release prep → Run workflow**.
   - Enter the target version (e.g. `1.3.0`). Do not include the `v` prefix.
   - The workflow opens a `release/vX.Y.Z` PR against `dev` that bumps
     `shared/__init__.py` and rewrites `CHANGELOG.md`.

3. **Review and merge the prep PR into `dev`.** Then merge `dev` into `main`
   the normal way (PR from `dev` → `main`).

4. **Tag `main` and push the tag.**

   ```sh
   git checkout main
   git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

5. **Watch the release workflow.** Pushing the tag triggers `release.yml`,
   which:

   - Verifies the tag matches `__version__` and that `CHANGELOG.md` has a
     matching `## [X.Y.Z] - YYYY-MM-DD` section and footer compare link.
   - Runs `python -m unittest discover tests`.
   - Extracts the changelog section for `X.Y.Z` and publishes it as the
     GitHub release body.

   If any step fails, no release is published — fix the issue and re-tag.

## Cutting a release by hand

If the prep workflow is unavailable, the same result can be produced locally:

```sh
python .github/workflows/release_tools.py prep 1.3.0
```

…then open a PR with the resulting changes.

## Re-running a failed release

If `release.yml` fails after publishing is already partially complete,
delete the tag (locally and on the remote) and any draft release, fix the
underlying issue, and re-push the tag:

```sh
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
```

## What is **not** automated

- Tag creation. Tagging `main` is still a deliberate human step.
- Package publication. Repo Lasso is not distributed via PyPI; users install
  by cloning the repo, so no artifacts beyond GitHub's auto-generated source
  tarballs are published.
- Tag signing. Historical tags are lightweight; keep doing that unless the
  project decides to sign going forward.
