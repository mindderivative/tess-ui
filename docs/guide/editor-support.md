# Editor Support: JSON Schemas

Tesserae ships JSON Schemas of what its files hold, for any tool that checks or completes a file against one: a script, a test, an editor
extension. They describe the **data** a `.tdl` file loads to (the front end `tess_ui.spec.tdl` turns a view into a plain mapping, keys in lower
snake_case, with `widget` for a node's block head), not the text of the file: the syntax of TDL itself (blocks, slots, comments) belongs to the TDL tools.
With a schema in hand, a tool knows the keys, style fields, theme colour roles and layout values, what each means, and can flag a mistake such as `Foregorund`.

| Schema | For |
| --- | --- |
| `tess-ui-widget-schema.json` | a view, `*_View.tdl`: one node, with a branch for each built-in widget and each view Tesserae ships, and its properties |
| `tess-ui-stylesheet-schema.json` | a stylesheet of rules, `*_Stylesheet.tdl` |
| `tess-ui-theme-schema.json` | a theme, `*_Theme.tdl` |

They are JSON Schema draft-07 and come with Tesserae: `tesserae schema` says where each is and what it is for.

## What the schemas cover

- **A view** (a `Widget` block) is described by `tess-ui-widget-schema.json`. It knows the keys every node has
  (`Name`, `Slot`, `State`, `Style`, `Classes`, `Handlers`, `A11y`, `Interaction`, `Visible`, `Route`,
  `Focus_Group`, `Window_Region`, `Tooltip`, `Params`, `Expects`; `If`, `For` and `Key` are wrappers the front end takes off again) and, for each built-in widget
  (`Container`, `Rect`, `Text`, `TextInput`, `Checkbox`, `Slider`, `Window`, ...) and each view Tesserae ships (`Button`, `Card`, ...), its properties or params
  with their types, choices and bounds. A value may be an expression (`<| width / 2 |>` in the file) wherever a number or a choice is. `Style` is every style field
  with what it takes.
- **Your own views** (`TaskItem { ... }`) are known once you add them: `tesserae schema --project` writes a copy of the widget schema that has every view the
  project has, with its params, so a tool completes a call of one and flags a misspelt param or a missing one. A view of yours that has the name of one
  Tesserae ships replaces it, as in the loader.
- **A stylesheet of rules** (`Widget`, `Variant`, `Size`, `Shape`, `Classes`, `Name`, `Part`, `State` and a `Style`) is described by
  `tess-ui-stylesheet-schema.json`; the states are the real ones, and `Style` is the same fields as a node's.
- **A theme** (`Seed`, `Dark`, `Colors`, `Typography`, `Components`, and `Styles` in the older rule shape) by `tess-ui-theme-schema.json`.

The page [TDL Reference](../api/tdl.md) is written from the same schemas, key by key.

## Finding them

```bash
tesserae schema             # where each schema is, and what it is for
tesserae schema --project   # the same, with the schema of this project's own views (writes .tesserae/tess-ui-widget-schema.json)
```

`--project` (here, or `--project DIR`) writes `.tesserae/tess-ui-widget-schema.json` in the project: the widget schema with your views in it. It is a snapshot: run
it again after you add a view or change a view's params (add `.tesserae/` to `.gitignore`).

## Checking a file against one

Read the file with the front end and validate the mapping it gives. This is what Tesserae's own tests do for every view, stylesheet and theme of the
repository:

```python
import json
from pathlib import Path

import jsonschema
from tess_ui import cli
from tess_ui.spec.tdl import load_tdl_file
from tess_ui.spec.tdl_theme import plain

schema = json.loads((cli.SCHEMAS / "tess-ui-widget-schema.json").read_text(encoding="utf-8"))
data = plain(load_tdl_file(Path("Views/Main_View.tdl")))
for error in jsonschema.Draft7Validator(schema).iter_errors(data):
    print("/".join(map(str, error.absolute_path)), error.message)
```

Keys in the data are the lower snake_case of the file's `Title_Case` (`Corner_Radius` is `corner_radius`), so that is how a schema names them.

## What it knows, and what it can't

It knows what Tesserae accepts of a built-in widget: the keys of a node and of its `A11y`, every property and what it takes,
every style field and what each takes (a dimension, a spacing, a layout keyword `tess_re` understands), the theme's colour roles
and type and shape tokens, the icon names and the window buttons. A key it doesn't know is flagged, which is how a typo shows.

It can't know what only your app knows:

- the ViewModel methods a `Handlers` entry names, or what a `<| |>` expression reads: `app.check()` compares them
  with the ViewModel without a window (see [Components & Embedding](components.md));
- your own views, unless `tesserae schema --project` has written them in (a snapshot);
- your own theme: a colour accepts any CSS colour, and suggests the theme roles.

## For contributors

The schemas are written by `tools/generate_schema.py` from Tesserae's own code (the widgets, style fields, tokens and icons), and ask
`tess_re` for the layout keywords, so none of it is typed by hand. Run it again after changing what a file may hold; `tools/generate_tdl_docs.py` then writes
the [TDL Reference](../api/tdl.md) from them. The tests check that the committed files are what the generator writes, and that every `.tdl`
file in the repository (the shipped views and stylesheets, the examples, the themes) validates against the schema of its kind.
