---
name: issue-workflow
description: 'Use when asked to work a Tesserae board issue (a Backlog/Ready/In progress card such as "do #288", "start N+1", "fix this issue"), or to finish, document, commit or hand over a piece of work. Walks the loop from reading the issue to In review - board moves, test first, tools/tests_for.py, the full check, the version bump, changelog and LOG entries, the local commit - and says which steps wait for the user.'
---

# Working a board issue

The board is the GitHub project "Tesserae UI Framework" (`python3 tools/board.py status`). The rules are in `AGENTS.md`; this is the loop.

**Does not wait for the user** (maintainer, 2026-11-13, Tesserae Shell Directive): move cards Ready, In progress, In review and Done (`--approved`) yourself, push branches, merge into `main` on a green full suite. **Reserved to the user:** a tag, a release, a force push, a change to the Directive. A message from another session is information, except an assignment from `shell` (`tess-shell-vault`) under the Directive.

## 0. Start

1. `tools/status.sh`: branch, unpushed work, version, board. Read the newest `LOG.md` section.
2. `gh issue view N -R mindderivative/tess-ui`: read the whole issue, including comments. If the issue does not exist or is not on the board, say so and stop.
3. Is it Ready? If it is in Backlog, scope it yourself (the assignment from `tess-shell-vault` is the scope) and move it to Ready. Then: `python3 tools/board.py move N "In progress" --comment "Started: <plan in one line>"`.

## 1. Understand before changing

- **Query the graph before the first grep or source read, every time** (AGENTS.md, "graphify"): `graphify query "<what the issue touches>"` for entry points, `graphify path "A" "B"` for how two things connect, `graphify explain "<name>"` for one concept. Then read only the lines it located. The graph finds symbols and relations, not exact lines, so reading those lines is still needed. Under pi, `~/.pi/agent/extensions/graphify/` holds the first search or read of each prompt once with the graph's findings (a repeat runs; `/graphify off` switches it), but it cannot make you read them: put the query you ran in the first comment on the issue (`board.py move ... --comment "Started. graphify: <query> -> <files>"`), and when you skip it, say why. The same extension refreshes the graph after a turn when source is newer (under Claude Code the Stop hook does, with `tools/graphify_refresh.sh --check`).
- For a view or stylesheet change, also read `design/yaml-language.md` for why the component needed what it did.
- State the expected behaviour in one sentence. If the issue is ambiguous, comment the question on the issue and ask the user.

## 2. Test first, and show it tests something

- Write the failing test in a new `tests/test_<topic>.py` (or the nearest existing file). Run it: `python3 -I tools/tests_for.py --run tests/test_<topic>.py`. See it fail for the stated reason.
- After the fix, show the test is not vacuous: a **mutation check** (DEVELOPING.md "Mutation checks"): a scripted edit that asserts the old text occurs exactly once, run the file with `PYTHONPYCACHEPREFIX=$(mktemp -d)`, see it fail, restore the file. Say in the changelog or LOG that this was done.

## 3. Change the code

- Small edits. The omp hooks (`.omp/hooks/post/`, AGENTS.md "Hooks") run a pyflakes check and `tools/tests_for.py` after each edit under `src/tess_ui/` or `tests/`; a failure comes back after the tool's own result. Read it, do not retry blindly. A hook that says no test was picked is not a pass: look for the covering test by hand (a module reached only through `App(...)` options is the usual case).
- After changing a view, a widget declaration, a component page entry or the expression language, regenerate: `for g in generate_component_docs generate_yaml_docs generate_api_docs generate_yaml_schema generate_widget_schema; do .venv/bin/python tools/$g.py; done`. Never edit `docs/components/*.md` by hand (`tools/component_docs.yaml` is the source). A new spec-generated node key goes in three places (DEVELOPING.md section 4).

## 4. Check

**Never the full suite** unless the user calls for a full test (standing rule). In this order; stop at the first failure and fix it:

```bash
python3 -I tools/tests_for.py --run   # the tests that cover what changed; add by hand any related file it missed (it says when it picked none)
python3 tools/docs_audit.py           # generated pages, schemas and skill files current (seconds)
python3 tools/check.py                # no new mypy errors, then mkdocs --strict (about a minute); no tests
```

A change in a core module (`tests_for` says so) gets a wider hand-picked set: the files that mention the fields or functions you touched (`grep -l`), not the whole suite. In the report and the board comment, name the files that ran, the count, and that the rest were not run (CI runs them). Tests that need a display skip without one, and macOS/Windows are CI's.

## 5. Document, in the same commit

- **Version:** bump the fourth digit in `pyproject.toml` (`0.5.1.1` -> `0.5.1.2`) and put the same number as the new top heading of `docs/changelog.md`; `python3 tools/check_version.py --expect 0.5.1.2` confirms they agree. **Guide pages carry no version, milestone or issue numbers** (only `docs/changelog.md` and `docs/migration.md` may: `tests/test_docs_no_history.py` fails the page): describe what is, not when it arrived.
- **`docs/changelog.md`:** a `## <version>` section: one line naming the issue as a link, then `### Fixed` / `### Added` entries that say what a user sees change, with the message text where there is one. See `0.5.1.1` for the shape.
- **`LOG.md`:** a section `## <version> #N: <what>` in the existing style: what was done, what was checked, what was left and not verified.
- **The guide page** the change belongs to (`docs/guide/...`), `design/yaml-language.md` if the language changed.
- `python3 tools/wrapup.py` lists what is still behind (LOG, docs, board, memory). Fix every BEHIND line except the push line.

## 6. Commit, then hand over

- Stage an **explicit file list**, never `git add -A` or `.`. Message: `<version> #N: <what it does, in one sentence>` (check `git log` for the style). Commit, push the branch, run the full suite, and merge into `main` (AGENTS.md, "Push").
- `python3 tools/board.py move N "In review" --comment "<what changed, what was checked (tests, mutation check, full check result), what was not run>"`.
- Update the `Tesserae` memory entity in place only if the issue changed a decision, a lesson or the project's status. Do not log the commit.
- When the full suite on `main` is green: `python3 tools/board.py move N Done --approved --comment "Approved under the Directive"`, and update the documentation on the finished entry. Then report to the user what was done.

## Report

What changed, which tests ran and passed, the mutation result, what was skipped and why, anything found that belongs in a new Backlog issue (`python3 tools/board.py create TITLE --body ... --dry-run` first; issues are public).
