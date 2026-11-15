---
name: tdl-view-authoring
description: Use when writing or changing a Tesserae view, stylesheet or theme (*_View.tdl, *_Stylesheet.tdl, *_Theme.tdl), a ViewModel that serves one, or the loader/schema code that reads them. Gives the file and naming rules, the node keys, how to validate without opening a window, the traps, and which generated files to regenerate.
---

# Writing views, stylesheets and themes (TDL)

Views, stylesheets and themes are TDL files, read by the TDL language 0.2 (the `tesserae-dl` library, Python 3.14). The language is documented in `docs/guide/view-language.md` (the whole language), `docs/guide/naming-convention.md`, `docs/guide/layout.md`, `docs/guide/bindings.md` (expressions) and `design/tdl-views.md` (how a TDL file maps to a view, and why). Read the page for what you touch; this skill is the checklist and the traps. Do not write from memory: check a property against the widget's declaration (`docs/api/tdl.md`, or `docs/schema/tess-ui-widget-schema.json`).

## Files and names

| File | Name is | Notes |
|---|---|---|
| `Counter_View.tdl` | `Counter` | a view; the `Name` of its root node is its **bind key**, keep it equal to the file name |
| `Counter_ViewModel.py` | `Counter` | class `CounterViewModel`, `views = "Counter"` |
| `Brand_Theme.tdl` | `Brand` | a `Theme { ... }` root: `Seed`, `Colors`, `Typography`, `Components` |
| `Tasks_Stylesheet.tdl` | `Tasks` | a `Styles { ... }` root holding rules; each names a `Widget` |

**Every file starts with a metadata block** between `---` lines: `TDL: 0.2`, `Name: <Name>` and `Tesserae: "0.6"` (the release series; a file of another line is refused, a missing line is noted once). `tesserae new` and `tesserae add screen` write it; always write it in new files. The root word of the body says the kind: `Styles` a stylesheet, `Theme` a theme, any other word a view (a widget). A docs block that shows a whole file is fenced ```tdl (or ```text with `title="Main_View.tdl"`); its metadata block is optional there (`tests/doc_blocks.py` puts one in front), a fragment is fenced ```text and is not read.

CamelCase file names. A view with `Params` is a component: another view calls it by name with the params as plain keys. A view whose root has no `Name` has no ViewModel. Keys are `Title_Case` (`Typography_Role`, `On_Click`, `A11y`); a key written `typography_role` is an error that says what to write. Values are never changed.

## A node

A block headed by its widget: `Button { Label: Save, Variant: filled }`. Keys every node has: `Name` (a handle, unique in the view), the wrappers `If <| expr |> { }` and `For i, it In <| expr |> Key <| expr |> { }`, `Slot`, `State`, `Style { }`, `Classes`, `Handlers { }`, `A11y { }`, `Interaction`, `Visible`, `Window_Region`, `Route`, `Focus_Group`, `Children { }`. **Anything else is a property of the widget**, and an unknown one is an error with the nearest suggestion. State (`Checked`, `Selected`, `Value`, `Disabled`) is a property, never a style.

Expressions are slots, `<| expr |>`: a safe Python subset with a fixed list of functions and the lookup order loop variable, local state, params, ViewModel, app, built-ins. A value that is exactly one slot is that expression (`Disabled: <| not ready |>`); text around slots is a template (`Text: Count: <| count |>`); a quoted string is plain text. **`{{ }}` in a `.tdl` file is refused.** A handler's statements are `Set { Target: x, Value: <| ... |> }`, `Call { Action: "name" }` and the names of ViewModel actions.

Ids are assigned by the loader (`root.add`, `root.children[0]`, `[key]` under a `For`); give a node a `Name` when a ViewModel, a stylesheet rule, a test or hot reload has to find it.

## Validate without a window

Never trust a view you have not loaded. In order, fastest first:

1. **Render it**: `python3 tools/shot.py <folder> --view Main --out /tmp/shots/x.png` (see the `live-check` skill). A mistake is a `LoadError` that names the file, line and column and the nearest valid name, for example `Main_View.tdl:7:5: error: Rect: no property 'colour' (properties: disabled)`; the message is the last line of the traceback.
2. **`assert app.check() == []`** in a test: it compares every name, action and `expects:` entry of the open views with their ViewModels. This is the cheap guard that a view and its ViewModel stay in step.
3. **Schema**: `tesserae schema --project` writes a schema that includes your own views for the editor (`docs/guide/editor-support.md`). `tests/test_schema.py` and `tests/test_widget_schema.py` check every `.tdl` file of the repository against the committed schemas.
4. **Tests**: `tests/helpers.py` has `view_from(text)` to build a `View` from a TDL view text (the metadata block first); `tests/test_pixels.py` has `opened(tmp_path, tdl)` for a headless window. A new test module that imports `tess_dl` or `tess_el` starts with `pytest.importorskip(...)` (the 3.12 CI jobs lack them).
5. **Formatting**: `tools/tdl_format.py` is the one place that spells a value as TDL for the generators; do not hand-roll that elsewhere.

## Stylesheet rules

A rule names a `Widget` (or only `Classes`, a `Name` or a `Style`), and may add `Variant`, `Size`, `Shape`, `Classes`, `Name`, a `Part` (a named node inside the widget's view) and a `State` (`hovered focused focus_visible pressed disabled selected checked expanded error read_only visited`). Specificity: a `Name`, then the count of matched properties (all `Classes` count as one), then a `State`, then the widget alone; a later rule wins a tie. A widget's shipped looks are the lowest layer, the app's stylesheet above them, and **a node's inline `Style` beats every rule for the fields it sets**.

## Traps

- **Old syntax.** The loaders read TDL only. A YAML view (`kind:`/`id:`, `widget:`, `{{ }}`) is not a view any more; `tesserae migrate-tdl [PATH] [--write]` moves a project (`docs/migration.md`). The YAML loaders and the old pipeline (`spec/expand.py`, `translate.py`, `*_Component.yaml` fragments) are being deleted: do not write against them.
- **Mistakes that are errors** (so a typo is not a rule that silently does nothing): a rule's `Part` that no node of the view has (`Card has no part 'heading' (did you mean 'headline')`; a part is a named node in the view's own TDL, and a built-in widget has none), and `Placement` or `Offset` with no `Anchor`.
- **Known gaps** (an open Backlog issue, so a silent no-op is not yet an error): an unknown key in a stylesheet file is not refused (#291). Do not rely on it being accepted; do not document it as supported.
- **`Foreground`** is a style extra of widgets that draw text or glyphs only; elsewhere it is an error that names who accepts it.
- A **spec-generated node key** (`spin`, `dial`, `graph`, `tooltip`) must be added in the places DEVELOPING.md section 4 lists (`build._NODE_KEYS`, `view._props_equal`) and be checked against the generators' node-key table in `tools/generate_tdl_docs.py` (`NODE_KEYS`).
- A docs example that uses `Part` names or expression lists is guarded by tests; keep the example true.

## After changing a view, a widget declaration, a component page entry or the expression language

Regenerate and commit the results, because tests compare them:

```bash
for g in generate_component_docs generate_component_order generate_tdl_docs generate_api_docs generate_schema; do .venv/bin/python tools/$g.py; done
python3 tools/docs_audit.py
```

`tools/component_docs.yaml` is the source of `docs/components/*.md`: edit it, never the pages. Then follow the `issue-workflow` skill (tests, full check, changelog, LOG).
