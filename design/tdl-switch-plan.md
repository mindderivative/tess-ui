# Switching tess-ui's files from YAML to TDL: plan and progress

Decided by the maintainer on 2026-11-14 (he is the only user, so no compatibility period for others). Evidence: the spike on branch `spike/tdl-views` (`spike/FINDINGS.md`, `spike/roundtrip.py`): all 61 shipped `*_View.yaml` convert to TDL and come back equal as data.

**How to resume:** every piece below is its own branch from `main`, in its own worktree beside the repo (`../tesserae-wt-<piece>`), small enough for one sitting. Work in progress is committed and pushed at the end of each step. `main` stays green and keeps loading YAML until piece 10, so stopping between any two pieces loses nothing. Tick a piece here when it is merged; the next unticked piece is next. The full suite runs only at the gates marked GATE; other pieces run the tests that cover them (`python3 -I tools/tests_for.py --run`), `tools/docs_audit.py` and `tools/check.py`.

## Decisions (from the spike)
- A node is a block headed by its widget (`Button { ... }`); `Name:` is its name; scalar keys stay properties; a dict value is a block headed by its (lower case) key; `children` is a block of nodes.
- `if:` is a wrapper `If <| cond |> { <node> }`; `for:` is `For x In <| items |> Key <| key |> { <node> }`.
- Handlers are blocks of steps: `Set { Target: name, Value: <| expr |> }` and `Call { Action: "name", Args: [...] }`; a step's value is one pure TEL expression. Steps run in order and each sees the earlier writes. Targets are plain names.
- TEL stays a pure expression language and is not changed. tess-ui's `expr.py` moves to TEL in its own track (piece 11).
- `tesserae: 0.6` becomes a metadata line `Tesserae: "0.6"`; comments are kept (`#`).
- Key casing (maintainer, 2026-11-14): **`Title_Case`** for keys of views, styles and themes, as the shell's files. A block head that is a map key is Title_Case too (`Style`, `Handlers`, `Children`); a node block is headed by its widget name (also CamelCase), so a block's role is told by position (inside `Children`, a block is a node) and by the schema, not by letter case. Piece 0 writes the exact rules and the key conversion table (`typography_role` -> `Typography_Role`).
- Tuple `for` targets (`i, it in enumerate(items)`, 10 uses; maintainer, 2026-11-14): the pair form is supported **later**, by TEL or TDL growing it. Until then the converter writes such a loop with a single variable and an `Index_And_Item` helper is NOT added; each of the 10 is listed in piece 2 with the rewrite used (e.g. iterate the list of `{index, item}` pairs built in the expression).
- Python 3.14 becomes the minimum (`tess_dl` needs it). `tess_dl` stays pinned to a git SHA until it is published.
- **Slot delimiters (maintainer, 2026-11-14, agreed with the `tess-dl` session): `<| expression |>`**, not `{{ }}`. Braces inside an expression (`{'a': {'b': 1}}`) are therefore ordinary text and need no care; text with a slot is a template (`Battery <| battery.percent |>%`). TEL itself is unchanged (it receives the text between the delimiters). `tess-dl` has paused its work to save usage, so the pinned `tess_dl` does NOT yet read `<| |>`: the plan goes on as if it did (see piece 1 and the risks). The `}}` problem and the stopgap space are gone.

## Pieces
Each piece lists what is done when it is ticked.

- [x] **0. Language mapping spec** (`design/tdl-views.md`, no code): every rule above written out, the casing and tuple-`for` decisions, what an error points at, the `If`/`For` wrapper effect on `part:` paths and hot reload.
- [ ] **1. TDL front end**: `spec/tdl.py` turns TDL text into the same node dict the YAML loader produces (the spike's reverse mapping, made real), with `file:line:column` errors from `tess_dl`. Both loaders exist side by side; nothing is switched. Tests: the 61 shipped views as TDL give dicts equal to their YAML. **Depends on `tess_dl` reading `<| |>`** (paused upstream): until it does, the front end keeps slot reading behind one small function and its tests run through a stand-in that rewrites `<| x |>` to `{{ x }}` for text without nested braces; the stand-in is deleted when `tess_dl` ships the delimiters. If the stand-in proves too awkward, do pieces 0 and 11 first and resume here.
- [ ] **2. Converter**: `tesserae migrate-tdl PATH [--write]` turns a view into TDL keeping comments, key order and layout, using the pair-target rule; idempotent. Tests on the shipped views and on edge cases.
- [ ] **3. Convert the 61 shipped views** to `*_View.tdl` (YAML kept beside them for now) with a test that each pair loads to the same dict. **GATE**: full suite.
- [ ] **4. Stylesheets**: front end and converter for `*_Stylesheet`, then the shipped stylesheets, same equality test.
- [ ] **5. Themes**: the same for `*_Theme`, including `Modes`-style columns if any.
- [ ] **6. Discovery, naming and the CLI**: `project.py` finds `*_View.tdl`, `*_Stylesheet.tdl`, `*_Theme.tdl`; `tesserae new` and `add screen` write TDL; examples and `apps/` converted. Tests for discovery and the templates.
- [ ] **7. Schemas and editor support**: the JSON schemas and docs generators describe TDL (reusing the shell's schema work where possible); the YAML schema generation goes.
- [ ] **8. Tests**: embedded YAML in tests becomes TDL in batches (helpers `view_from` and `opened` take TDL). One batch per sitting, listed here as it goes: ____
- [ ] **9. Docs**: the ~140 pages and tutorials, in batches (guide, components, stylesheets, themes, tutorials, README). `tools/docs_audit.py` and the strict build pass each batch.
- [ ] **10. Cutover. GATE**: delete the YAML loaders, the converter's YAML input (keep it as a one-shot script outside the package), the `pyyaml` dependency and the YAML generators; Python 3.14 minimum in CI and `pyproject.toml`; changelog and migration page; full suite.
- [ ] **11. TEL track** (independent of 1 to 10, can run before or after): register tess-ui's built-in functions (`format_date`, `current_date`, `date_add_days`, ...) with `tess_el`, an adapter for tess-ui's name lookup order, then replace `expr.py`; the handler `Set`/`Call` runtime moves to the step blocks.

## Risks to watch
- Tree shape: the `If`/`For` wrappers add a level. Pieces 1 and 6 must keep `part:` paths, `name` lookup and hot reload working.
- `tess_dl` is unpublished and misses helpers its docs promise (`Block.properties`, `get`, `blocks`, `walk`); tess-ui reads `entries` until it has them.
- `tess_dl` has not shipped `<| |>` (paused): pieces 1 to 5 depend on it or on the stand-in above; the converter writes `<| |>` from the start.

## Progress log
(append one line per merged piece: date, piece, commit)
- 2026-11-14: piece 0 done: `design/tdl-views.md` (the front end returns the same node dict, wrappers removed again, so the tree shape downstream is unchanged).
