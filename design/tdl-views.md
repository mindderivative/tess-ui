# Tesserae views, stylesheets and themes in TDL: the mapping

Piece 0 of `design/tdl-switch-plan.md`. Evidence: `spike/FINDINGS.md` on branch `spike/tdl-views` (all 61 shipped views round-trip as data). TDL syntax is in the `tess-dl` repository (`docs/language.md`), expressions are TEL; neither is changed by this note except the slot delimiters, which are `<| |>` (maintainer and `tess-dl`, 2026-11-14).

**The contract for the front end (piece 1):** reading a TDL view produces the *same node dict* the YAML loader produces today (`{widget, name, style, children, ...}`, with `{{ }}` still the template form inside strings), plus the same position maps. Everything after loading is unchanged. That is why the wrappers below cost nothing downstream.

## File
```
---
TDL: 0.2
Name: Button
Tesserae: "0.6"
---
# comments are kept
Button { ... }
```
- `Name` is the view's name (the `name:` of the YAML root, or the file stem when it has none); `Tesserae` is the release series (was the first line `tesserae: 0.6`), a quoted string. The root block is the root node.
- File names: `<Name>_View.tdl`, `<Name>_Stylesheet.tdl`, `<Name>_Theme.tdl`.

## Keys are Title_Case
Every key becomes `Title_Case`: each part between underscores gets a capital: `typography_role` -> `Typography_Role`, `on_click` -> `On_Click`, `a11y` -> `A11y`, `max_lines` -> `Max_Lines`. Back: lower-case the key. This is lossless because every shipped key is lower snake_case (the converter refuses a key that is not). It applies to node keys, style fields, param names, handler events, a11y fields and every map key. Values (enum words such as `filled`, widget names, `name` values, the text of a string) are never changed.

## Nodes
- A node is a block headed by its widget: `Button { ... }`. `name:` is `Name: spinner` (a value, kept as written).
- A scalar key is a property: `Label: "Save"`, `Disabled: true`, `Width: 100`. A list of scalars is a TDL list: `Choices: [filled, tonal]`.
- **A map value is a block headed by its key**: `Style { Flex_Direction: horizontal }`, `A11y { Role: button }`, `Params { Label { Type: str, Default: "" } }`.
- **`Children { <node blocks> }`** holds the child nodes in order.
- **Role by position:** a block directly inside `Children`, `If` or `For` is a node; any other block inside a node is a map. Letter case never decides it (a widget head and a key head are both Title_Case), so the front end knows the context while it walks and the schema checks the names.

## If and For are wrappers
```
If <| loading |> {
  Circular_Progress { Name: spinner }
}
For item In <| items |> Key <| item['value'] |> {
  Chip { Name: chip }
}
```
- `if: expr` -> `If <| expr |> { node }`; `for: x in xs` + `key: k` -> `For x In <| xs |> Key <| k |> { node }`. A node with both has the `For` outside and the `If` inside it (the `if` is tested for each item).
- **The front end removes the wrappers again**: it hands the node on with `if`, `for` and `key` set, exactly as the YAML loader does. Instance ids and paths (`root.cp.panel`), `part:` rules, names and hot reload therefore see the same tree as today; nothing downstream knows the wrapper exists. (This is the answer to the tree-shape risk in the plan.)
- The expression texts keep their TEL form; `<| |>` is only the container.
- **Tuple targets** (`for: i, it in enumerate(items)`, 10 uses): language 0.2 gives a `For` several variables, so the converter writes `For i, it In <| enumerate(items) |> Key <| ... |>` as the YAML says it (no rewrite, no TODO line, nothing to report; until 0.2 they were written with one variable `i_it`). The front end reads `For.variables` back as `i, it in enumerate(items)`.

## Expressions
- A value that is exactly one slot: `Text: <| label |>`; text around a slot is a template: `Text: Battery <| level |>%`, read as the template string `Battery {{ level }}%` for the existing loader. A quoted string is plain text (a `<|` inside quotes is not a slot).
- The slot text is handed to TEL as is (`tess_el` origin from the slot's text origin: the column of a mistake is exact). Braces, `}}`, quotes and `#` inside an expression are ordinary text.
- `tess-dl` 0.2 reads `<| |>` itself (language 0.2, `tesserae-dl>=0.2.0,<0.3`): the front end hands the text to `tess_dl.loads` and takes `Slot.text`; the earlier stand-in is gone. A file that says `TDL: 0.1` (slots `{{ }}`) is refused at its version line with a hint to `tools/migrate_slots.py` of the tess-dl repository.

## Handlers are step blocks
```
Handlers {
  On_Click {
    Set { Target: open, Value: <| not open |> }
    Call { Action: "on_toggle" }
    Call { Action: "surface.dismiss" }
    Call { Action: "pick", Args: [<| row['ref'] |>], Index: <| i |> }
  }
}
```
- Steps run in order; each sees the writes of the earlier ones. `Set` writes a plain name (the shell's and tess-ui's existing writable-name rules decide which names are writable, at load time). `Call` names a ViewModel or built-in action; `Args` are TEL expressions, other properties are keyword arguments. Every value is one pure TEL expression: TEL gets no assignment and no `;`.
- The front end turns steps back into the handler text the existing runtime takes (`open = not open; on_toggle()`), so nothing downstream changes until the TEL track (piece 11) gives steps their own runtime.
- A handler event key is a property when it is a bare action name (`On_Click: save` has no step form needed; none in the shipped views).

## Errors and positions
- Syntax errors come from `tess_dl` as `file:line:column: message (hint)`.
- The front end supplies the same position maps the YAML loader does: a key's origin (the key text), a value's origin (the value text; for a slot, the position after `<| `). A load error then points at the right place in the `.tdl` file with the same wording as today.
- A key that is not Title_Case, a map block where a node is expected and a `Set` whose `Target` is not a plain name are errors that say what to write.

## Stylesheets and themes
- A stylesheet is a root `Styles { }` (the old `styles:` list) holding one `Rule { ... }` block per rule, in order (order breaks ties); a rule's keys are Title_Case (`Widget: Button`, `Variant: filled`, `State: hovered`, a `Style { ... }` block). Exact shape: "What piece 4 decided", below.
- A theme is a root `Theme { }` with the old keys as Title_Case blocks and properties (`Seed`, `Dark`, `Colors { ... }`, `Typography { ... }`, `Components { ... }`). Detailed in piece 5.
- The stylesheet is written exactly (piece 4); the theme is still a sketch: piece 5 starts by converting two real files and writes the exact shape here.

## What is not decided
- Whether `If` and `For` ever get a `Name` of their own (not needed today).
- The exact TDL for the 10 tuple loops (later).
- How `Handlers` keyword arguments are named when a keyword clashes with `Action` or `Args` (none in the shipped views).

## What piece 1 decided (the front end, `src/tess_ui/spec/tdl.py`)
Entry points: `load_marked_tdl(text, file, resolver=None)` and `load_tdl_file(path)` return the `PMap` that `nodes.load_marked` returns for YAML; `nodes.parse_data(data, text, file)` takes either (`parse_view` is `parse_data(load_marked(...))`), so the later switch of the loader is a choice by file suffix. Nothing calls the front end yet.
- **Positions.** A key's position is the key text; a block's, its head word (a node's `at` is its widget). A value's is its first character, except: a quoted string is positioned after the quote (as YAML), a slot or template at the start of the `<|`, so the existing `{{ }}` string and its offsets land on the same columns (`<| |>` and `{{ }}` have the same width). The `if` and `key` texts are trimmed expressions positioned at their first character; the `for:` string is `x in items` and is positioned so that the parser's offset of the iterable lands on the items text in the `For` line. `key_at` of `if`/`for`/`key` is the `If`, `For` and `Key` word.
- **Handlers lose exact columns.** The handler text is built from the steps (`a = b; c(d, e=f)`), so an expression error inside it points at the event's block, not at the column inside the step, until piece 11 gives steps their own runtime. Spacing of the text differs from a YAML handler's (it is the same program).
- **Handler forms.** An event that is a bare action name stays a property (`On_Click: save`); a block of steps is statements, so `Call { Action: x }` alone is `x()`, not `x`. `Call` writes `Action(args..., keyword=value...)` with the keys of the other properties lower-cased; `Args` and every `Value` are slots only (a literal is written `<| 1 |>`); `Action` is a (dotted) name.
- **`For` without a key.** A `For` must write a `Key`; `Key <| None |>` means no `key:` on the node.
- **Wrappers.** At most one `For` (outside) and one `If` (inside) per node; an `If` or `For` must hold exactly one node; an `If` with an `Else` is refused; wrappers are only read among nodes (in `Children`, in another wrapper, in a node-typed property), never as an entry of a node or a map.
- **Maps and lists.** A block that is not `Children`, `Handlers` or a node-typed property is a map; a block that holds nothing but `Item` blocks is a list of maps (tooltip `Actions`, rich-text `Runs`), so a map whose only key is `item` cannot be written. Inside a map, a block whose key starts with `On_` and holds only `Set`/`Call` steps is a handler text (the tooltip actions' `on_click`). A property the widget declares as `node` or `nodes` (found through the registry or the `resolver`) is a block holding one node or the nodes.
- **Keys.** Round-trippable `Title_Case` only: lower-casing must give a key that `title_case` writes back as given (`MaxLines`, `max_lines`, `MAX` are refused with `write 'Max_Lines'`). A key with `__` is allowed.
- **Values.** `true`, `false`, `null` words are the YAML values; any other word is text; `50%` is the text `"50%"`; a `name(...)` call is an error (nothing in a view takes one yet).
- **Metadata.** `TDL`, `Name`, `Tesserae` only; `Tesserae` goes through `marker.scan` (same problems, written `Tesserae:`), and is optional as the YAML first line is. The metadata `Name` is not the node's `name` (the root block's own `Name:` property is); nothing compares it with the file name yet (piece 6).
- **Errors.** `tess_dl`'s errors keep its wording and hint, at the same line and column (a slot's position is the start of its `<|`, `text_origin` where its text starts). A file in an older language (`TDL: 0.1`) is a `LoadError` at its version: this file is written in TDL 0.1; Tesserae reads TDL 0.2.
- **The stand-in** (piece 1 to 5) hid braces and quotes inside a slot so `<| |>` could be read as `{{ }}`; piece 3b deleted it (`_standin_rewrite`, `_standin_words`, `_slot_text`, the mask tables). `spec/tdl.LANGUAGE_VERSION` (`"0.2"`) is what the front end accepts and the converters write.
- **Test helper.** `tests/tdl_helper.py` was a test-only YAML-to-TDL writer (the seed of piece 2); it is now a thin wrapper over the real converter (`tess_ui.migrate_tdl`, below). The 10 pair loops are written `For i, it In <| enumerate(items) |>`, as in the YAML, so the two mappings compare equal as they are.

## What piece 2 decided (the converter, `src/tess_ui/migrate_tdl.py`, `tesserae migrate-tdl PATH [--write] [--remove-source]`)
- **Output is checked.** Every result is read back with `spec/tdl.py` and compared (types kept, key order and the spelling of handler statements not) with the YAML loader's mapping before it counts; a form that does not read back is a `ConvertError` with the YAML line and what to write, never a nearly right file. A file that fails is reported and left alone; the other files are still written.
- **Comments and blank lines are kept.** An own-line comment goes above the entry that follows it (a comment above a node's `if:`, `for:` or `widget:` key goes above its wrapper or head), a comment at the end of a line goes at the end of the line of the entry that began there (`- widget: Text  # c` is on `Text {`), the comments at the top of the file go above the root block, those after the last entry at the end of the file. A blank line between entries is kept (a run of them is one). Comments in a handler's Python text go with its steps (above the step, or at the end of its line). A `#` in a list is written `# `.
- **Layout.** Two spaces to a level, one entry to a line. Block YAML is always opened. A YAML flow mapping that sits on one line is one line (`Label { Type: str, Default: "" }`) when the line is at most 150 columns, else opened one entry to a line; a scalar list is `Key: [a, b]`, wrapped at 150 columns with the continuation lines under the first item, and one item to a line when it has comments in it; a `Set` or `Call` step is one line, opened when over 150 columns; an event with one step is `On_Click { Set { ... } }` on one line, with more steps one step to a line; a node with nothing but its widget is `Slot { }`. A `Handlers` or `Children` block, and every node, is always opened. A comment is never wrapped. Line ends are those of the source (CRLF in, CRLF out); the output has no byte order mark.
- **Names.** The metadata `Name` is the root's `name:` when it is a TDL name, else the file name's stem (`Button_View.yaml` is `Button`); the root block keeps its own `Name:` property. `Tesserae` is written when the YAML had its first line, with that line's comment.
- **Values.** `50%` is written bare (`Width: 100%`), a word that is not `true`, `false` or `null` is written bare, other text quoted with the JSON escapes TDL reads; text with a slot is written unquoted when TDL can read it (no quote, `,`, `{`, `}`, `]`, ` #`, no leading or trailing space) and is refused otherwise, with the hint to make the whole value one slot. A slot's text is kept as written (`{{ x }}` is `<| x |>`); a handler's expressions are the author's source text when on one line.
- **Handlers.** `Handlers` events: a bare (dotted) action name or a number or null or empty text stays a property; otherwise statements become steps: an assignment to one plain name is a `Set`, an augmented assignment is a `Set` with the operation spelled out (`x += 1` is `Value: <| x + 1 |>`, noted in the report: a new value, not changed in place), a call of a (dotted) name with positional and keyword arguments is a `Call` (`Args:` for the positional ones, a keyword is its own `Title_Case` property); anything else (a bare name among statements, `a[0] = 1`, `a = b = 1`, `a, b = ...`, `*args`, `**kw`, `if`, a keyword argument named `action` or `args`) is refused. An `on_*` key of a node itself (a view's own `on_pick` param) is text; an `on_*` key inside a map (a tooltip action) is steps when its text reads as statements, text otherwise.
- **Nodes and maps.** `if:` is `If <| ... |>`, `for:` is `For x In <| ... |> Key <| ... |>` (`Key <| None |>` without a `key:`), the `For` outside the `If`. `children:` is `Children { }`, a node-typed property (`node` or `nodes` in the registry or in a view's `params:` found beside the file) a block with the node or nodes, a list of mappings `Key { Item { } Item { } }`, an empty mapping `Key { }`. A property that looks like a node of a widget the converter does not know is written as a map and noted.
- **Pair loops.** `for: i, it in enumerate(items)` is written `For i, it In <| enumerate(items) |> Key <| ... |>` (piece 3b; before it, `For i_it In` with a `# TODO tuple for-target` line and a report). Nothing is rewritten and nothing reported.
- **Refused**, with file, line and what to write: a key that is not lower snake_case or is `if`/`else`/`for` (or a block named `in`/`key`), a widget name that cannot head a block, an anchor or alias, a value that is not text, a number, yes/no or null (a YAML date), a list of lists or a list that mixes maps and text, `key:` without `for:`, a `for:` that is not `name in expression`, an expression that has `|>` or a line end, a view in the older syntax (`kind:`; run `tesserae migrate-yaml`), a series line that is not the current one.
- **Files.** A dry run lists what would be converted and writes nothing; `--write` writes `<Name>_View.tdl` beside the YAML (only when it differs: a second run is `current` and touches nothing); a differing `.tdl` is replaced only with `--write`; the YAML stays unless `--remove-source` (with `--write`) and then only for the files written or already current. Stylesheets, themes and components found under PATH are skipped with a note (pieces 4 and 5). Exit code 1 when a file failed, 2 for a wrong argument. Python 3.14 (`tess_dl`) is needed, and the command says so when it is missing.

## What piece 4 decided (stylesheets: `src/tess_ui/spec/tdl_stylesheet.py`, `src/tess_ui/migrate_tdl_sheets.py`)
Surveyed first: the 49 shipped sheets (276 rules), the 9 under `examples/` and `apps/shell_config`, and the tests'. Every one is `tesserae:` + `styles:`; a rule has only `widget`, `style` and optionally `part`, `variant`, `size`, `shape`, `state`, `classes` (a list of names; `name` is allowed by the loader and unused in the shipped files); of the 525 style values in the shipped sheets 112 are slots (all of them one whole-value `"{{ ... }}"`, none mixed with text), 42 are a map one level deep (`padding`, `transition`, `corner_radius`, `margin`) and the rest are numbers, words (token names such as `on_surface_variant`) and `true`. No anchors, no handlers, no `style:` that names a `*_Style.yaml` in a shipped file.
```
---
TDL: 0.2
Name: Button
Tesserae: "0.6"
---
# comments
Styles {
  Rule { Widget: Button, Size: xs, Style { Height: 32, Gap: 4 } }
  Rule {
    Widget: Button
    Part: label
    State: hovered
    Classes: [a, b]
    Style {
      Background: <| 'primary' if (not toggle or selected) else 'surface_container_highest' |>
      Padding { Left: 12, Right: 12 }
      Transition { Corner_Radius: 200, Elevation: 200 }
    }
  }
}
```
- **Root and rules.** The root block is `Styles` and holds `Rule` blocks only, in file order (`order` of the rule is its place). The metadata `Name` is the file stem (`Button_Stylesheet.tdl` is `Button`); `Tesserae` as in a view. Nothing is a node: `If`, `For`, `Children`, `Handlers` are errors here; a property or a block that is not `Rule` directly in `Styles` is an error that says `Styles holds Rule blocks`.
- **A rule** has its keys as `Title_Case` properties (`Widget`, `Variant`, `Size`, `Shape`, `State`, `Part`, `Name`, `Classes: [a, b]`) and one `Style { }` block. Any key is read, so `RuleSheet.of` says `a rule has no 'colour'` in its own words, with the position in the `.tdl`.
- **Style fields** are properties (`Height: 40`); a field that holds a map is a block of its own (`Padding { Left: 12 }`, `Transition { ... }`); a block holding nothing but `Item` blocks is a list of maps (as in a view). A slot is the `{{ expr }}` string the YAML had (`Padding: <| {'left': 12} |>` is a whole-value expression: TEL's braces need no care). Token references (`outline`, `on_surface_variant`, `primary`) are words and stay bare; text that is not a word is quoted. A `style:` that names a `*_Style.yaml` file is the text it is (`Style: Compact_Style.yaml`); the includes are expanded by `load_stylesheet`, not by the marked path.
- **What the front end returns** is the mapping the marked YAML loader hands `RuleSheet.of`: `{styles: PSeq of rule PMaps}` with `at`, `key_at`, `val_at`, `item_at` everywhere. A rule's position is its `Rule` word, a key's the key text, a value's its first character (a quoted string after its quote, a slot at `<|`), a block's its head word (`Style`, `Padding`), the `styles` key and list the `Styles` word. A mistake `RuleSheet.of` finds therefore keeps its message and hint and points at the same word in the `.tdl`; an `Expr`'s origin lands on the expression text (checked for the 224 templates of the shipped sheets in both files). Entry points: `load_marked_tdl_stylesheet(text, file)`, `load_tdl_stylesheet_file(path)`, `load_rule_sheet_tdl(path, parts_of=None)` (`load_rule_sheet` for a `.tdl`). Nothing calls them yet (piece 6 chooses by suffix). `load_stylesheet` (themes.py, the plain dict with includes expanded) has no TDL twin yet: it is piece 6's, with discovery.
- **Errors** from `tess_dl` keep its wording (a duplicate property key is its "The key X is already used on line N"); mine: not `Styles`, `Styles holds Rule blocks, got 'Rul'` (nearest name), a property in `Styles`, an `If`/`For` anywhere, a key that is not Title_Case (as views), a duplicate `Style` block.
- **The converter** (`convert_sheet(text, name, file)`, in `migrate_tdl_sheets.py`) is `migrate_tdl`'s own, with the stylesheet's two levels: a `_Converter` subclass whose `styles:` list is `Styles { }` and each rule `map_block("Rule", ...)`, so comments, blank lines, layout and the 150-column rule are the views' (a flow rule `- {widget: Button, size: xs, style: {...}}` is one `Rule { ... }` line when it fits, a block rule is opened one entry to a line, its `Style` stays inline when the YAML had it inline). No `on_` key is a handler here. The result is read back through the front end and compared (types kept, key order not) with the YAML loader's mapping; `styles:` empty or absent is `Styles { }` and reads back as no rules.
- **Refused** (with the YAML line, what to write): a top-level key other than `styles` (with `looks_like`'s hint: a theme or a view), `styles:` that is not a list, a rule that is not a mapping, an empty file or one that is not a mapping, and every refusal of a view's values and keys (anchor, date, a key not lower snake_case or a TDL keyword, text with a slot that cannot sit unquoted, a list of lists, a series line that is not the current one).
- **Files.** `tesserae migrate-tdl` now also converts `*_Stylesheet.yaml` to `*_Stylesheet.tdl` beside it (same rules: a dry run writes nothing, a second run is `current`, `--remove-source`, exit codes). Themes and components are still skipped with the note `a theme or component: only views and stylesheets are converted so far`; a single file that is none of view or stylesheet is `is not a *_View.yaml or *_Stylesheet.yaml file`; an empty folder says `no view or stylesheet files found`. `migrate_tdl.py` changed only in its driver (`_SHEET`, the dispatch and these messages).
- **Shipped.** The 49 `src/tess_ui/views/*_Stylesheet.tdl` are written beside their YAML; `tests/test_tdl_shipped_sheets.py` checks each is current, loads to the YAML mapping, gives `RuleSheet` the same rules and has expression origins on the text.
## What piece 5 decided (themes: `src/tess_ui/spec/tdl_theme.py`, `src/tess_ui/migrate_tdl_theme.py`)
Evidence: every theme the repository has (8 `Brand_Theme.yaml` in the examples, all the same file, and Tesserae's own `src/tess_ui/spec/default_theme.yaml`, which has comments, a `styles:` list and dotted component keys) and a synthetic theme with every key the loader takes (`seed`, `dark`, `colors`, `typography` with all five fields, `components` with both fields and variants, `styles`).
```
---
TDL: 0.2
Name: Brand
Tesserae: "0.6"
---
Theme {
  Seed: "#0B6B58"
  Dark: false
  Colors { Tertiary: "#C2410C" }
  Typography {
    Body_Large { Font_Family: Inter, Font_Size: 17 }
  }
  Components {
    Card {
      Corner_Radius: 12
      Elevated { Elevation: 1 }
    }
  }
}
```
- **File and root.** `<Name>_Theme.tdl` beside `<Name>_Theme.yaml`; Tesserae's `default_theme.yaml` becomes `default_theme.tdl` (the command takes both names; `Name` is the file name without `.yaml` and without `_Theme`). The root is one `Theme { }` block, anything else is an error at its line. `Name` and `Tesserae` are the metadata as in a view; `Tesserae` is optional as the first line is.
- **The mapping is a plain dict.** A YAML theme has no position maps, so `load_theme_tdl(text, file)` returns what `yaml.safe_load` + marker strip gives (`seed`, `dark`, `colors`, `typography`, `components`, `styles`); `load_marked_theme_tdl` returns the same as `PMap`s with positions for a pointed error. `load_theme_tdl_file(path)` is `load_theme` for a TDL file: it also expands a rule's `style: X_Style.yaml`, runs `check_theme` and the font check and names the file in its `ValueError`s.
- **Keys** are `Title_Case` as everywhere (`on_primary` is `On_Primary`, `body_large` is `Body_Large`). `Seed` and `Dark` are properties; `Colors`, `Typography`, `Components`, `Styles` are blocks. A key a theme does not have (`Colours`) is an error at the key with the loader's wording, `unknown field ..., expected one of ...`, and a "did you mean".
- **Colours are quoted strings.** `Seed: "#0B6B58"`, `Primary: "#FF000080"`; a bare `#` is `tess_dl`'s error `This colour needs quotes` with the line and column. A role name (`Tertiary: primary`), a token (`Elevation: level_2`) and a family (`Font_Family: Inter`) are words and need no quotes; text with a space is quoted. Numbers, `true`/`false` and `null` keep their types (`Font_Size: 17` is an int, `Tracking: -0.25` a float).
- **Typography** is `Typography { Role { Field: value } }`, roles and fields `Title_Case`, plain maps (a one-line YAML `{a: 1}` stays one line up to 150 columns).
- **Components.** A component key with a dot (`card.elevated`) cannot be a TDL key, so a variant is a block inside its component: `Card { Corner_Radius: 12, Elevated { Elevation: 1 } }` is `card` and `card.elevated`; a block holds the component's fields (properties) and its variants (blocks, to any depth: `Split_Button { Tightened { Pressed { ... } } }` is `split_button.tightened.pressed`); a component with variants and no fields is just its variants. A property directly in `Components` is the key as written, so the loader says what is wrong with it. Limits: **the order of a component's own key and its variants is normalised** (the own key first: `card.elevated` before `card` is read back as `card`, `card.elevated`; the dict is equal, and a component lookup is by key); an empty own mapping next to variants (`card: {}` and `card.elevated`) has no form and is refused, not dropped.
- **`Styles`** (a theme's own rule list, the older `kind`/`classes`/`id` shape that the docs say is not how a view is styled now) is the generic list of maps of a view: `Styles { Item { Kind: Rect, Style { Corner_Radius: 0 } } }`. Piece 4 may give stylesheets a `Rule` block; the theme's list stays `Item` until the cutover decides (it is the only shipped use, `default_theme.yaml`).
- **Comments, blank lines, key order and layout** are kept as in piece 2 (the same machinery: own-line comments go above the entry that follows, an end-of-line comment stays on the entry that began there, the header comments above `Theme {`); a trailing comment of a block head (`Card {  # round`) stays on the head. Every result is read back through `load_theme_tdl` and compared (types and all) with the YAML mapping before it counts; a form with no TDL form is a `ConvertError` with the YAML line. An unknown top-level key is refused at its line.
- **Command.** `tesserae migrate-tdl` now also converts `*_Theme.yaml` and `default_theme.yaml` (a file named on the command line or found under a folder), same flags and exit codes, same `current`/`converted`/`failed` report; the hook is a branch in `migrate_tdl.migrate_tdl` that calls `migrate_tdl_theme.theme_result`.
- **Not decided / not done.** Nothing loads `.tdl` themes yet (piece 6 does discovery; `load_theme_tdl_file` is the function the loader calls then); `Modes`-style columns do not exist in tess-ui themes (they are the shell's), so there is nothing to carry.

## What piece 6a decided (loading `.tdl` everywhere: names, loaders, shipped set, hot reload, templates)
- **One rule, the suffix.** `spec/flavour.is_tdl`: a file named `*.tdl` is read by the TDL front ends, any other name by the YAML ones. The branch is in `nodes.read_marked` (views; `parse_view`), `rules.load_rule_sheet`, `themes._load_mapping` (`load_stylesheet`, `load_theme`), `marker.note_if_missing`, `ViewLibrary._declared` and `build.shipped_default_theme`, each a single `if` on the suffix, so removing YAML at the cutover is deleting the other branch. `require_tdl` says what to install when `tess_dl` is missing.
- **Names.** `project.KINDS` keeps the YAML suffixes; `TDL_SUFFIXES` has the TDL ones for view, theme and stylesheet (components, `*_Style.yaml` and ViewModels have none); `suffixes(kind)` is `(tdl, yaml)`. In one folder a name found as both is the `.tdl` and the YAML twin is noted once at INFO (`Project._note_twin`); the same name in two folders is the same "in two places" error, naming the suffix of the first. The not-found message is unchanged (`(Name_View.yaml)`), and `_elsewhere` (the wrong-folder hints of the earlier hint work) matches either suffix. `view_stem`, `is_view_file`, `sibling_file` replace the `removesuffix("_View.yaml")` sites (`app`, `naming`, `component`, `window_view`, `resolve_view`, `resolve_embedded`, `ViewLibrary.project_sheet`).
- **Kind of a TDL file** is its root word (`project.kind_of_tdl`, no parse): `Styles` is a stylesheet, `Theme` a theme, any other word a view. `tdl_wrong_kind` gives the hint and the root word's line and column; the loaders raise it as `this looks like a theme: name it Brand_Theme.tdl` (the suggested name ends in `.tdl` for a `.tdl` file, `.yaml` otherwise: `looks_like_kind`). A name that says another kind (`load_theme("A_Stylesheet.tdl")`) is refused as `*.yaml` files are.
- **The marker.** The TDL series line is the `Tesserae` metadata the front end already checks with `marker.scan` (newer: upgrade; older or malformed: the sentence of the first-line key, written `Tesserae:`); a file without it is noted once, as a YAML file without its first line is.
- **Only language 0.2.** `TDL: 0.1` was already refused at its version for all three kinds (`_parse_document` is shared). New: a `{{ }}` in a string or in the text around slots is refused too (`_Front.refuse_old_slot`, in `value`, so views, stylesheets and themes alike), because the front ends spell a slot `{{ }}` inside, and a quoted `"{{ x }}"` would have become a live template. A text with literal `{{` cannot be written in a `.tdl` file; there is no fallback.
- **The shipped set.** `spec/flavour.shipped_flavour()` is `tdl` unless `TESS_UI_SHIPPED=yaml` or `tess_dl` is not importable (the 3.12 jobs have no `tess_dl`); read each call, so a test sets it, and the shipped caches (`_SHEETS`, `_RULES`, the default theme) are keyed by it. `ViewLibrary`, `shipped_sheet`, `shipped_rules` and the default theme follow it. `ViewLibrary.decl` caches a view's params by file and reads a `.tdl` through the front end with itself as the resolver (a view being declared answers `None` to itself).
- **Hot reload** needed nothing beyond the loaders: the watchers keep paths and call the loaders; `tests/test_tdl_discovery.py` has the TDL twins (view edit, mistake, the sheet beside a view, theme files).
- **Templates and the CLI.** The five view templates are `*_View.tdl.tmpl` (converted with the real converter, then parametrised; the title is quoted); `add screen` in a window project prints `Name { Name: ..., Route: "...", Style { Flex: fill } }` for the `screens` block. The YAML schema globs of `tesserae schema` are YAML-only and unchanged.
- **Tests that assumed YAML shipped files** (`test_text_field` schema check, `test_view_stylesheets` file names) read the YAML twin / record `.tdl` as `.yaml`; `test_cli`, `test_language_marker`, `test_widget_schema` expect TDL from `new`. Side-by-side equality: `tests/test_tdl_discovery.py` (61 view trees, 61 composed host trees, 49 stylesheets, three themes).

