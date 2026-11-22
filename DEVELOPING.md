# Developing Tesserae

Everything needed to go from a clean OS install to a working checkout. (The standing rules for the AI assistant are in `CLAUDE.md`; this file is
for a person or a fresh session.)

## 1. The machine

Tesserae is pure Python on top of `tess_re` (the `tesserae-engine` package, imported as `tess_re`), which is Rust built with `maturin`. The checkout was developed on
Fedora/Nobara and then CachyOS, both with KDE Plasma on Wayland; CI also runs Windows and macOS.

```bash
# Fedora / Nobara
sudo dnf install git python3 python3-devel gh gcc pkgconf-pkg-config fontconfig-devel
# Debian / Ubuntu: sudo apt install git python3 python3-venv python3-dev gh build-essential pkg-config libfontconfig1-dev
# CachyOS / Arch: sudo pacman -S git python github-cli base-devel pkgconf fontconfig
```

On Arch the headers ship in the `python` and `fontconfig` packages and `venv` is built in, so there are no `-devel` or `python3-venv` packages to add. The suite and
`mkdocs build --strict` were checked on CachyOS (Python 3.14.7, Wayland session): 7791 passed, 4 skipped.

Python 3.14 or newer. `gh auth login` once, with the `project` scope (`gh auth refresh -s project`), to use the board.

## 2. The checkout and the venv

```bash
git clone https://github.com/mindderivative/tess-ui.git && cd tess-ui
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pip install mkdocs mkdocs-material   # the docs build; also pillow-based tools need no extra
```

`pip install -e ".[dev]"` pulls `tesserae-engine==0.6.11` and `tesserae-el==0.2.0` (`import tess_el`, the expression language) from PyPI (`import tess_re`; pinned to the release the whole suite was run on); nothing else is needed. A newer `tess_re` is tried first in a throwaway venv (`python3 tools/tre_version_check.py` says when there is one), then the pin moves. The suite is run on the PyPI build of 0.6.11 (CI; not run locally for this move). To work against an unreleased tess_re, build its wheel (`pip install maturin`, then in the tess_re checkout `maturin build --release -m
crates/engine-py/Cargo.toml`) and `pip install --force-reinstall --no-deps` it into a scratch venv.

Never put a scratch tess_re build into `.venv` by accident; to try another tess_re version make a throwaway venv (`python3 -m venv /tmp/v055`, install the wheel and
`pip install -e . --no-deps` plus the dependencies).

## 3. Checking your work

```bash
python3 -I tools/tests_for.py --run                 # the tests that cover what changed (seconds): the usual check
tools/fullcheck.sh                                  # the whole suite, then `mkdocs build --strict` (about 3 minutes): only when the maintainer asks
.venv/bin/python -m pytest tests/test_toolbar.py -q   # one file
```

A commit needs the tests that cover its change to pass; the full suite runs when the maintainer calls for it, and in CI. Tests run against a headless window whose `window.snapshot()` draws shaders, gradients and backdrop blur, so
`tests/test_pixels.py` reads those back by pixel (see its helpers); what a snapshot cannot tell you is how it *feels* (timing, scroll snap) or looks to a person. A real display is needed for
`tools/window_perf.py` and anything that opens a second OS window while running.

Some tests read tess_re's source: `TESS_RE_SOURCE_DIR=<path to the tess_re checkout>` lets the one real-font test run.

### Generated files (the tests compare them)

After changing a view, a widget declaration, a component page entry or the expression language, regenerate and commit the results:

```bash
for g in generate_component_docs generate_tdl_docs generate_api_docs generate_schema; do
  .venv/bin/python tools/$g.py
done
```

`tools/component_docs.yaml` is the source of `docs/components/*.md`; do not edit those pages by hand.

Every shipped view, stylesheet and theme, example and whole-file docs block carries `Tesserae: "0.6"` in its metadata block (`src/tess_ui/spec/marker.py`: `LINE`, the first two parts of the version). A new series changes `LINE` and every one of those files; `tests/test_language_marker.py` fails while any lacks it.

The generators read the shipped `.tdl` files through the TDL front ends (never the YAML twins that are left until the cutover). `tools/component_docs.yaml` stays YAML: it is the component-page generator's own data (prose and TDL usage examples), read by `tools/` only, so `pyyaml` stays a development dependency for it, for `tools/component_order.yaml` and for the skills check.

### Mutation checks

How a new test is shown to test something: break the code it covers (change a value, drop a branch) in a scripted edit that **asserts the text occurs exactly
once**, run the test file with an isolated bytecode cache (`PYTHONPYCACHEPREFIX=$(mktemp -d)`), see it fail, restore the file.

## 4. How the project is laid out

- `src/tess_ui/views/` — the shipped views: `<Name>_View.tdl` (structure, params) and `<Name>_Stylesheet.tdl` (looks, by widget/variant/size/part/state).
- `src/tess_ui/spec/` — the view language: `nodes.py` (parser), `compose.py` (composition, route records), `lower.py` (to the builder's spec), `build.py`, `effects.py`, `transition.py`.
- `src/tess_ui/composed.py` — the live view: wires handlers, overlays, timers, focus groups, frames, measures. `app.py` — the app; `appwindows.py` — more windows.
- `design/yaml-language.md` — the language, and a log of why each component needed what it did. `design/component-order.md` — the build order of the 0.5.0 components.
- `docs/` — the MkDocs site; `docs/changelog.md` and `CHANGELOG.md`; `LOG.md` and `PLAN.md` — the project log and plan.
- Spec-generated node keys (`spin`, `dial`, `graph`, `tooltip`) must be added in two places: `build._NODE_KEYS` and `view._props_equal`.

## 5. Working rules (from `AGENTS.md`)

- **Commit locally** as soon as a milestone, step or feature is finished and the tests that cover it pass (no full suite unless asked). Match the style of `git log`. Push the finished task to its own `feat/<id>` or `fix/<id>` branch and open a PR; **never push to `main`, force-push, push a tag, merge or release without being told to.**
- Update the docs (the changelog, `design/yaml-language.md`, the component page, a `mkdocs build --strict`) with each finished piece.
- The board is the GitHub project "Tesserae UI Framework" (owner `mindderivative`, number 2): Backlog → Ready → In progress → In review → **Done only after the merge and a green suite on `main`**. Move items with `python3 tools/board.py move 124 "In review"`; comment on the issue with what was built, how it was tested, and what was not built or not checked.
- Report outcomes as they are: say what was not run or not seen.

## 6. A release (continuous delivery; the maintainer's word starts it, one approval ends it)

A release is a commit on `main` whose `pyproject.toml` version has no tag yet. `.github/workflows/release.yml` does the rest when CI finishes green on that commit:

1. The maintainer says to release. Release commit "Tesserae X" on a branch (version in `pyproject.toml`, the `## X` heading of `docs/changelog.md`, a `LOG.md` entry; `python3 tools/check_version.py --expect X --pypi`), a pull request marked `[full-ci]` (the ruleset needs the PR and the `CI result` check), merged when green.
2. CI runs on the merge commit. When it is green the Release workflow's `plan` job sees an untagged version and goes on; for an already tagged version it does nothing (the run summary says so).
3. `build` checks the dependencies and the changelog, builds the sdist and wheel, installs the wheel from PyPI's dependencies and runs the whole suite and four examples against it.
4. `publish` waits at the `pypi` environment: **the maintainer approves it** (Actions, the run, Review deployments). The agent never approves it.
5. `github-release` waits for the index, installs `tesserae-ui==X` in a clean environment and imports it, then creates the tag `vX` on the release commit and the GitHub Release (notes = the changelog section, wheel and sdist attached, marked latest).
6. Afterwards: the `Tesserae` memory entity, the board (`tools/board.py move N Done --approved`).

A run that failed after CI was green is retried with "Run workflow" on Release (`workflow_dispatch`): the upload skips files already on PyPI and the Release is created only if it does not exist. The workflow's own token creates the tag and the Release, so they start no other workflow.

### What CI runs

`.github/workflows/ci.yml` chooses one of three modes with `tools/ci_plan.py` (the rules are in its docstring; try it on your own commits with `python3 -I tools/ci_plan.py --base origin/main`):

| Mode | When | What runs |
|---|---|---|
| `docs` | every changed file is documentation (`docs/`, `design/`, `.agents/`, root `*.md`, `mkdocs.yml`) | the docs checks only |
| `partial` | everything else: the normal run | the tests `tools/tests_for.py` picks, with the importers of a core module included; five smoke tests when nothing is picked (they include `tests/test_examples_run.py`, which runs six example apps); a changed example picks that test and its own |
| `full` | called for, or the release series moves up | the whole suite (which runs the example apps), and the platform jobs (clean install, built executable) |

Called for: run the workflow by hand with mode `full`, label the pull request `full-test`, or put `[full-ci]` in the head commit's message or the pull request's title. The series moves up when the first three parts of the version change (`0.5.1.x` to `0.5.2`). The docs checks (`tools/docs_audit.py`, `mkdocs build --strict`, the tests that read the docs) run in every mode, and the platform jobs also run in `partial` when a packaging file changed (`pyproject.toml` beyond its `version` line, the templates, `cli.py`, `build.py`).

CI gotchas: a leading-slash path is not absolute on Windows; the macOS runner asks for reduced motion, so a test must not assume the OS state.

## 7. Display notes (KDE Plasma, Wayland)

Real windows can be opened from a shell; the person at the machine drives them. Wayland lets an app neither place nor centre a window and ignores `always_on_top`, so
window position code is a no-op there. Resizing a window on tre 0.5.4 stalls frames; 0.5.5 and later do not.

### A bare test run stays off your session

Some tests open a window (`App.run(max_frames=...)`, the example apps, the built executable) and write the OS clipboard through `tess_re`. `tests/conftest.py` therefore drops `DISPLAY`, `WAYLAND_DISPLAY`, `WAYLAND_SOCKET`, `DBUS_SESSION_BUS_ADDRESS` and `XDG_SESSION_*` from a local run, and points the `XDG_*` folders and `TESS_UI_STATE_DIR` at a private temporary folder; the tests that need a display skip, as on CI's Linux. The pytest header says what was dropped. `TESS_UI_ALLOW_REAL_SESSION=1` allows the real session, for a run by hand on purpose. A run on GitHub Actions (`GITHUB_ACTIONS=true`) is left alone, since its jobs run under their own `xvfb-run` display; a bare `CI` variable does not count, because other tools (an agent's shell) set it next to the real display. The same run renders on Mesa's software Vulkan (lavapipe, `VK_ICD_FILENAMES`) where it is installed, as CI does, not on the machine's own GPU. A test must never use a system-wide input device (`/dev/uinput`), the real pointer or clipboard, or a state-changing call to the person's bus or services; if it must, mark it opt-in with a stated reason.

The whole suite runs in parallel: `pytest -n 4` (pytest-xdist, in the dev extra) took 1m42 on this machine against about five minutes serial, with the same tests passing; CI's full run uses `-n auto`.

## 8. Agent tooling

Moved from `AGENTS.md`.

* **Hooks (omp):** TypeScript modules, `.omp/hooks/pre/*.ts` before a tool call and `post/*.ts` after it; omp does not run the shell hooks of `.claude/settings.json`, so `.claude/hooks/*.sh` act only under Claude Code. A hook is read when a session starts. Tests: `node --experimental-strip-types .omp/hooks/test_hooks.ts`.
  * `pre/git-guard.ts`: blocks any signal by name or pattern (`pkill`, `killall`, `pgrep -f`, `kill $(pgrep ...)`; signal only a PID you started), a force push and a push of tags; checks a `git commit` first with pyflakes-level ruff over the Python files it will hold (staged, a same-command `git add`, or `-a`).
  * `post/ruff-edit.ts`: the same check on a file just edited under `src/` or `tools/`.
  * `post/tests-for-edit.ts`: runs the tests `tools/tests_for.py` picks (capped at 25 seconds).
  * `post/after-commit.ts`: the memory and board reminder. `post/stop-docs.ts`: asks once for docs when `src/` changed and no documentation did.
* **`tools/tests_for.py [--run] [FILES]`** picks the tests that cover a change by imports and names; a changed `examples/<name>/` file picks `tests/test_examples_run.py` and the tests that name the example. It misses a test that reaches the code only through another module. It is not the full check.
* **graphify under pi:** the Claude Code `hook-guard` and Stop hooks of `.claude/settings.json` do not fire under pi, so `~/.pi/agent/extensions/graphify/` (global, outside the repo) holds the first search or read of each prompt once with the graph's findings (query the graph, or repeat the call to run it) and refreshes the graph after a turn when source is newer. `/graphify off|on|status` switches the guard; tests: `node --experimental-strip-types test_graphify.ts` in that folder.
* **CI:** `tools/ci_plan.py` picks docs, partial or full; a full run is a label, a `[full-ci]` mark or a manual run.
