# Tesserae views, stylesheets and themes in TDL: the mapping

Piece 0 of `design/tdl-switch-plan.md`. Evidence: `spike/FINDINGS.md` on branch `spike/tdl-views` (all 61 shipped views round-trip as data). TDL syntax is in the `tess-dl` repository (`docs/language.md`), expressions are TEL; neither is changed by this note except the slot delimiters, which are `<| |>` (maintainer and `tess-dl`, 2026-11-14).

**The contract for the front end (piece 1):** reading a TDL view produces the *same node dict* the YAML loader produces today (`{widget, name, style, children, ...}`, with `{{ }}` still the template form inside strings), plus the same position maps. Everything after loading is unchanged. That is why the wrappers below cost nothing downstream.

## File
```
---
TDL: 0.1
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
- **Tuple targets** (`for: i, it in enumerate(items)`, 10 uses) have no TDL form yet (maintainer: added later to TEL or TDL). The converter writes them with one variable and lists each in piece 2 with its rewrite; it refuses silently-wrong output.

## Expressions
- A value that is exactly one slot: `Text: <| label |>`; text around a slot is a template: `Text: Battery <| level |>%`, read as the template string `Battery {{ level }}%` for the existing loader. A quoted string is plain text (a `<|` inside quotes is not a slot).
- The slot text is handed to TEL as is (`tess_el` origin from the slot's text origin: the column of a mistake is exact). Braces, `}}`, quotes and `#` inside an expression are ordinary text.
- Until `tess-dl` reads `<| |>`, the front end's slot reading is one small function and the tests use a stand-in that rewrites `<| x |>` to `{{ x }}` for text without nested braces; the stand-in is deleted when the delimiters ship.

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
- A stylesheet is a root `Styles { }` (the old `styles:` list) holding one `Rule { ... }` block per rule, in order (order breaks ties); a rule's keys are Title_Case (`Widget: Button`, `Variant: filled`, `State: hovered`, a `Style { ... }` block). Detailed in piece 4.
- A theme is a root `Theme { }` with the old keys as Title_Case blocks and properties (`Seed`, `Dark`, `Colors { ... }`, `Typography { ... }`, `Components { ... }`). Detailed in piece 5.
- These two are sketches: pieces 4 and 5 start by converting two real files each and write the exact shape here.

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
- **Errors.** `tess_dl`'s errors keep its wording and hint, with `{{ }}` said `<| |>` while the stand-in is in; a pair target `For i, it In` gets the hint that the pair form is not supported yet.
- **The stand-in** is the block at the top of `tdl.py` (`_standin_rewrite`, `_standin_words`, `_slot_text`, the mask tables): it hides braces, quotes and backslashes inside a slot so an expression with `}}` in it (`{'a': {'b': 1}}`) reads too, which the plain `{{ x }}` rewrite of the plan could not. Deleting it is one change in that block.
- **Test helper.** `tests/tdl_helper.py` was a test-only YAML-to-TDL writer (the seed of piece 2); it is now a thin wrapper over the real converter (`tess_ui.migrate_tdl`, below). The 10 pair loops are written with one variable (`i, it in enumerate(items)` -> `For i_it In <| enumerate(items) |>`) and their bodies are not rewritten.

## What piece 2 decided (the converter, `src/tess_ui/migrate_tdl.py`, `tesserae migrate-tdl PATH [--write] [--remove-source]`)
- **Output is checked.** Every result is read back with `spec/tdl.py` and compared (types kept, key order and the spelling of handler statements not) with the YAML loader's mapping before it counts; a form that does not read back is a `ConvertError` with the YAML line and what to write, never a nearly right file. A file that fails is reported and left alone; the other files are still written.
- **Comments and blank lines are kept.** An own-line comment goes above the entry that follows it (a comment above a node's `if:`, `for:` or `widget:` key goes above its wrapper or head), a comment at the end of a line goes at the end of the line of the entry that began there (`- widget: Text  # c` is on `Text {`), the comments at the top of the file go above the root block, those after the last entry at the end of the file. A blank line between entries is kept (a run of them is one). Comments in a handler's Python text go with its steps (above the step, or at the end of its line). A `#` in a list is written `# `.
- **Layout.** Two spaces to a level, one entry to a line. Block YAML is always opened. A YAML flow mapping that sits on one line is one line (`Label { Type: str, Default: "" }`) when the line is at most 150 columns, else opened one entry to a line; a scalar list is `Key: [a, b]`, wrapped at 150 columns with the continuation lines under the first item, and one item to a line when it has comments in it; a `Set` or `Call` step is one line, opened when over 150 columns; an event with one step is `On_Click { Set { ... } }` on one line, with more steps one step to a line; a node with nothing but its widget is `Slot { }`. A `Handlers` or `Children` block, and every node, is always opened. A comment is never wrapped. Line ends are those of the source (CRLF in, CRLF out); the output has no byte order mark.
- **Names.** The metadata `Name` is the root's `name:` when it is a TDL name, else the file name's stem (`Button_View.yaml` is `Button`); the root block keeps its own `Name:` property. `Tesserae` is written when the YAML had its first line, with that line's comment.
- **Values.** `50%` is written bare (`Width: 100%`), a word that is not `true`, `false` or `null` is written bare, other text quoted with the JSON escapes TDL reads; text with a slot is written unquoted when TDL can read it (no quote, `,`, `{`, `}`, `]`, ` #`, no leading or trailing space) and is refused otherwise, with the hint to make the whole value one slot. A slot's text is kept as written (`{{ x }}` is `<| x |>`); a handler's expressions are the author's source text when on one line.
- **Handlers.** `Handlers` events: a bare (dotted) action name or a number or null or empty text stays a property; otherwise statements become steps: an assignment to one plain name is a `Set`, an augmented assignment is a `Set` with the operation spelled out (`x += 1` is `Value: <| x + 1 |>`, noted in the report: a new value, not changed in place), a call of a (dotted) name with positional and keyword arguments is a `Call` (`Args:` for the positional ones, a keyword is its own `Title_Case` property); anything else (a bare name among statements, `a[0] = 1`, `a = b = 1`, `a, b = ...`, `*args`, `**kw`, `if`, a keyword argument named `action` or `args`) is refused. An `on_*` key of a node itself (a view's own `on_pick` param) is text; an `on_*` key inside a map (a tooltip action) is steps when its text reads as statements, text otherwise.
- **Nodes and maps.** `if:` is `If <| ... |>`, `for:` is `For x In <| ... |> Key <| ... |>` (`Key <| None |>` without a `key:`), the `For` outside the `If`. `children:` is `Children { }`, a node-typed property (`node` or `nodes` in the registry or in a view's `params:` found beside the file) a block with the node or nodes, a list of mappings `Key { Item { } Item { } }`, an empty mapping `Key { }`. A property that looks like a node of a widget the converter does not know is written as a map and noted.
- **Pair loops.** `for: i, it in enumerate(items)` is written `For i_it In <| enumerate(items) |> Key <| ... |>` (the names joined by `_`) with `# TODO tuple for-target: i, it in enumerate(items)` above the `For`, and reported (file, line of the `for:`, original text, rewrite, and that the body still uses the second name and must use `i_it[0]`, `i_it[1]`). The converter never rewrites the body.
- **Refused**, with file, line and what to write: a key that is not lower snake_case or is `if`/`else`/`for` (or a block named `in`/`key`), a widget name that cannot head a block, an anchor or alias, a value that is not text, a number, yes/no or null (a YAML date), a list of lists or a list that mixes maps and text, `key:` without `for:`, a `for:` that is not `name in expression`, an expression that has `|>` or a line end, a view in the older syntax (`kind:`; run `tesserae migrate-yaml`), a series line that is not the current one.
- **Files.** A dry run lists what would be converted and writes nothing; `--write` writes `<Name>_View.tdl` beside the YAML (only when it differs: a second run is `current` and touches nothing); a differing `.tdl` is replaced only with `--write`; the YAML stays unless `--remove-source` (with `--write`) and then only for the files written or already current. Stylesheets, themes and components found under PATH are skipped with a note (pieces 4 and 5). Exit code 1 when a file failed, 2 for a wrong argument. Python 3.14 (`tess_dl`) is needed, and the command says so when it is missing.
