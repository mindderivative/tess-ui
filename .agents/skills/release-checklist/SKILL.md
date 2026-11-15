---
name: release-checklist
description: Use when preparing, checking or cutting a Tesserae release (a version bump, the release commit, the GitHub Release, the PyPI publish), or when asked "is it ready to release". Walks the version, checks, docs and release steps in order and separates what Claude may do from what waits for the user's separate instruction.
---

# Release checklist

The process is written in `DEVELOPING.md` section 6 and `.github/workflows/release.yml`. This skill is the ordered checklist, with the stops that need the user.

**Standing rule (CLAUDE.md): a release needs the user's word. Merging the release commit, approving the `pypi` environment and moving an issue to Done each need the user's separate, explicit instruction. A past approval does not carry over to the next release.**

## 1. Pre-flight (read-only)

- `tools/status.sh` for the overview. Clean `git status`, on the branch the user named. If the branch or version they name is not there, say so and ask before planning anything else.
- Every issue in the release is In review or Done on the board (`python3 tools/board.py status`), each with a comment of what was checked and what was not.
- Anything that could not be verified here (Windows, macOS, other GPUs, other compositors) is listed in the notes as not verified, not dropped.
- The version is free on PyPI: `python3 tools/check_version.py --pypi` (PyPI never accepts a version twice).
- The engine pin: `python3 tools/tre_version_check.py`. A tess_re release outside `<0.6` is a new Tesserae line, not a bump.

## 2. Version

The version is in `pyproject.toml` and the newest heading of `docs/changelog.md`. Bump both, then `python3 tools/check_version.py --expect X` and search for the old string for other places. Historical "since 0.5.x" notes in the guides stay as they are.

## 3. Checks

```bash
python3 tools/docs_audit.py     # generated pages and schemas current (fast)
python3 tools/check.py --full   # types, the whole suite, then mkdocs --strict (about three minutes): a release is the user's call for a full test; ask first, and say if it was not run
python3 tools/wrapup.py         # what LOG.md, docs, the board, memory are behind on
```

Tests that need a display skip without one: say so. CI runs `full` by itself when the version's first three parts change (`0.5.1.x` to `0.5.2`); for a point release in the same series it runs `partial`, so ask the user whether to call for a full CI run (a `[full-ci]` mark in the release commit, or a manual run with mode `full`). CI also runs Windows and macOS; their results are read from CI, never assumed.

## 4. Documentation

- `docs/changelog.md` (the heading is the version), `LOG.md` (a dated entry in the existing style), the migration page if anything a user writes changed, `README.md` and `docs/installation.md` if install steps changed.

## 5. Commit, then stop

Release commit "Tesserae X" in the repo's style (check `git log`). Tell the user what is ready and wait.

## 6. After the release commit is merged (continuous delivery)

`.github/workflows/release.yml` takes over when CI is green on the merge commit (DEVELOPING.md section 6): build, wheel tests, then the `pypi` environment. **The user approves the `pypi` environment; Claude does not.** After approval the workflow installs the published package, creates the tag `vX` and the GitHub Release (notes from the changelog, marked latest). Nothing is created by hand: do NOT run `gh release create` (it would take the tag from the workflow and make it fail).

Claude may: tell the user the run is waiting at `pypi` (`gh run list --workflow release.yml`), retry a failed run with `gh workflow run release.yml`, read the run's logs, smoke-test the published `tesserae-ui==X` in a scratch venv, add the `LOG.md` entry, and update the `Tesserae` memory entity only after the published package installs. The board moves to Done with `tools/board.py move N Done --approved` only after the user approves.

## Report

What was run and passed, what was skipped and why, which issues remain held.
