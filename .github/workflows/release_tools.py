"""Helpers used by release.yml and release-prep.yml.

Subcommands:
    check <tag>      Fail unless tag, __version__, and CHANGELOG.md agree.
    notes <tag>      Print the CHANGELOG section body for <tag> to stdout.
    prep  <version>  Rewrite shared/__init__.py and CHANGELOG.md for a new release.
"""

from __future__ import annotations

import datetime
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "shared" / "__init__.py"
CHANGELOG = ROOT / "CHANGELOG.md"
COMPARE_URL = "https://github.com/homebysix/repo-lasso/compare"

VERSION_RE = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
# Matches both "## [1.2.0] - 2024-06-23" and the legacy "## 1.0.0 - 2021-03-29".
RELEASED_SECTION_RE = re.compile(r"^## \[?(\d+\.\d+\.\d+)\]? - \d{4}-\d{2}-\d{2}")


def read_version() -> str:
    match = VERSION_RE.search(VERSION_FILE.read_text())
    if not match:
        sys.exit(f"Could not find __version__ in {VERSION_FILE}")
    return match.group(1)


def strip_v(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def split_changelog(text: str) -> tuple[str, list[tuple[str, str]], str]:
    """Return (header, [(section_header, section_body), ...], footer).

    ``footer`` is the trailing block of ``[x.y.z]: ...`` compare links.
    """
    lines = text.splitlines()
    footer_start = next(
        (i for i, line in enumerate(lines) if re.match(r"^\[[^\]]+\]:\s*http", line)),
        len(lines),
    )
    body = "\n".join(lines[:footer_start])
    footer = "\n".join(lines[footer_start:])

    sections: list[tuple[str, str]] = []
    current_header: str | None = None
    current_body: list[str] = []
    preface: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current_header is None:
                preface = current_body[:]
            else:
                sections.append((current_header, "\n".join(current_body).strip("\n")))
            current_header = line
            current_body = []
        else:
            current_body.append(line)
    if current_header is not None:
        sections.append((current_header, "\n".join(current_body).strip("\n")))

    return "\n".join(preface).rstrip() + "\n", sections, footer


def find_section_body(sections: list[tuple[str, str]], version: str) -> str | None:
    for header, body in sections:
        match = RELEASED_SECTION_RE.match(header)
        if match and match.group(1) == version:
            return body.strip()
    return None


def check(tag: str) -> None:
    if not tag.startswith("v") or not SEMVER_RE.match(strip_v(tag)):
        sys.exit(f"Tag {tag!r} must match vX.Y.Z")
    version = strip_v(tag)

    declared = read_version()
    if declared != version:
        sys.exit(
            f"Tag {tag} does not match __version__={declared!r} in {VERSION_FILE.name}"
        )

    _, sections, footer = split_changelog(CHANGELOG.read_text())
    if find_section_body(sections, version) is None:
        sys.exit(f"CHANGELOG.md has no section for {version}")
    if not any(line.startswith(f"[{version}]:") for line in footer.splitlines()):
        sys.exit(f"CHANGELOG.md footer is missing a compare link for [{version}]")

    print(f"OK: {tag} matches __version__ and CHANGELOG.md")


def notes(tag: str) -> None:
    version = strip_v(tag)
    _, sections, _ = split_changelog(CHANGELOG.read_text())
    body = find_section_body(sections, version)
    if body is None:
        sys.exit(f"CHANGELOG.md has no section for {version}")
    print(body)


def prep(version: str) -> None:
    if not SEMVER_RE.match(version):
        sys.exit(f"Version {version!r} must be X.Y.Z")

    VERSION_FILE.write_text(
        VERSION_RE.sub(f'__version__ = "{version}"', VERSION_FILE.read_text(), count=1)
    )

    text = CHANGELOG.read_text()
    header, sections, footer = split_changelog(text)
    if not sections or not sections[0][0].startswith("## [Unreleased]"):
        sys.exit("CHANGELOG.md must start with a '## [Unreleased]' section")

    unreleased_body = sections[0][1].strip()
    if not unreleased_body or unreleased_body.lower().startswith("nothing yet"):
        sys.exit("CHANGELOG.md [Unreleased] section is empty — nothing to release")

    today = datetime.date.today().isoformat()
    new_sections = [
        ("## [Unreleased]", "Nothing yet."),
        (f"## [{version}] - {today}", unreleased_body),
        *sections[1:],
    ]

    prior_version = next(
        (m.group(1) for h, _ in sections[1:] if (m := RELEASED_SECTION_RE.match(h))),
        None,
    )
    if prior_version is None:
        sys.exit("Could not find a prior released version in CHANGELOG.md")

    footer_lines = footer.splitlines() if footer else []
    kept = [line for line in footer_lines if not line.startswith("[Unreleased]:")]
    new_footer_lines = [
        f"[Unreleased]: {COMPARE_URL}/v{version}...HEAD",
        f"[{version}]: {COMPARE_URL}/v{prior_version}...v{version}",
        *kept,
    ]

    parts = [header.rstrip()]
    for section_header, section_body in new_sections:
        parts += ["", section_header, "", section_body.strip()]
    parts += [""] + new_footer_lines
    CHANGELOG.write_text("\n".join(parts) + "\n")

    print(f"Prepared release v{version} (previous: v{prior_version})")


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    cmd, arg = sys.argv[1], sys.argv[2]
    if cmd == "check":
        check(arg)
    elif cmd == "notes":
        notes(arg)
    elif cmd == "prep":
        prep(arg)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
