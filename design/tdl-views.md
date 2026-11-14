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
