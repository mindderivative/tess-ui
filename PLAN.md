# PLAN

Where tess-ui stands and what comes next. History is in `LOG.md` and `docs/changelog.md`; the plan of the September building-block program (M34-M53) is archived in `PLAN_ARCHIVE_M34-M53.md`. Work items are GitHub issues on the board "Tesserae UI Framework" (`python3 tools/board.py status`).

## Where it stands (2026-11-20)

- Released: tesserae-ui 0.6.3 (PyPI, import `tess_ui`), on `tesserae-engine` 0.6.8 (`tess_re`), `tesserae-el` 0.2.0 (expressions), `tesserae-dl` 0.2 (TDL files) and `tesserae-utils` 0.2.2 (colours, images). Python 3.14 is the floor.
- Views, stylesheets and themes are TDL (`*_View.tdl`, `*_Stylesheet.tdl`, `*_Theme.tdl`); YAML is no longer read. The switch is finished: `design/tdl-switch-plan.md` (history).
- Releases run through `release.yml` after green CI on `main`; the maintainer approves the `pypi` environment. See `DEVELOPING.md`, section 6.
- Every shipped stylesheet has a generated docs page (#291).

## Next

1. Cutover leftovers: YAML-era wording in comments, docstrings and tools (a `{{ }}` or `.yaml` that should say `<| |>` or `.tdl`), and the JSON schema's `{{ parameter }}` pattern for a theme's style values (to check: it may be dead since YAML went).
2. Speed of one sync (`View.reconcile`): about 12 ms for a window of a few hundred nodes, proportional to all nodes instead of the ones that changed. Plan in `LOG.md` (the Configuration Application, C5 part 3).
3. `COMPONENT_LIST.md`: the Material 3 components still to audit; it has no status marks yet.

## Not planned

- Anything for macOS and Windows beyond what CI shows; the maintainer's machine is Linux.
