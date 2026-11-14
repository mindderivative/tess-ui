# Spike: shipped YAML views as TDL (2026-11-14)

Throwaway: `yaml2tdl.py` converts a `*_View.yaml` to TDL text; `tess_dl.parse` (a6f1010) then checks it. Branch `spike/tdl-views`, not for merge.

## Result
- 61 of 61 shipped `*_View.yaml` convert and parse with **zero syntax errors** (Button, Card, Dialog and Menu looked at by eye).
- This shows only that the text is valid TDL. It does **not** show that a view survives the round trip: the converter is incomplete (below) and nothing loads the TDL back into a view.

## Mapping used
| YAML | TDL |
|---|---|
| `widget: Container` | block head `Container { ... }` |
| `name: x` | `Name: x` |
| `style: {a: 1}`, `handlers`, `a11y` | child blocks `Style { a: 1 }` (head capitalised) |
| `children: [...]` | `Children { <node blocks> }` |
| `params: {label: {type: str, ...}}` | `Params { label { type: str, ... } }` |
| `if: cond` (166 uses) | wrapper `If {{ cond }} { <node> }` |
| `"{{ expr }}"` alone | a bare slot `{{ expr }}` |
| `[a, b]` | `[a, b]` |
| `tesserae: 0.6` first line | metadata line `Tesserae: "0.6"` |

## Findings
1. `if:` cannot be a property: `If` is reserved, so the node moves inside an `If` wrapper. Fits TDL well (it is first-class there), but it changes tree shape: stylesheet `part:` paths, `name` lookups and hot reload must see through the wrapper.
2. `for:` (33 uses) and `key:` need `For x In {{ items }} Key {{ k }} { <node> }`. **Not implemented in the spike converter** (the keys are dropped), so the 33 `for:` nodes are not covered by the 61/61.
3. Strings mixing text and a slot (2 found): in TDL a quoted string treats `{{` as plain text, so these must be written unquoted as templates, with the comma, brace and `#` limits on unquoted text. The spike quotes them, which is wrong for those 2.
4. Slots containing `}}` inside (2 found, dict literals such as `{'a': {'b': 1}}`): TDL ends a slot at the first `}}`. These need rewriting or a space (`} }`) in the expression, or TEL must accept it.
5. Comments: the long header comments in each view are lost by this converter. A real converter has to carry them (TDL keeps `#` comments).
6. Key casing: kept lowercase `snake_case`; the shell's TDL uses `Title_Case`. Choosing one is a language decision, not a technical one.
7. YAML flow maps (`{width: 1, height: 2}`) become one-line blocks only with a head word, so every nested map needs a name for its block. Fine for style/handlers/a11y, but free-form maps (a handler table, `choices`) need case-by-case rules.
8. Scalars are not typed: TDL words are lexical, so `true` and `null` become schema-typed by tess-ui's own widget declarations (it already has them).

## Not done
Stylesheets and themes (49 more files), a reverse conversion, loading into the view model, error messages, expression slots with TEL-incompatible text, tests and docs.

## Read
The syntax is not the obstacle. The work is the tree-shape change from `if:`/`for:` wrappers and the editor/loader plumbing around it. Another 2 to 3 days would settle items 2 to 4 and do a real round trip on 10 views; the estimate of 3 to 4 weeks for the full switch stands (not made more precise by this spike).
