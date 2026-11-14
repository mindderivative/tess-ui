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

## TEL compatibility of the views' expressions (checked with tess_el from /home/phil/Projects/pyDev/projects/tess-el, `compile_expression`, language 0.1)
Every slot, condition and handler text in the 110 shipped view and stylesheet files was compiled (unique texts only).

| Kind | Unique | Compile | Fail | Why |
|---|---|---|---|---|
| `{{ }}` slots | 512 | 506 | 6 | 5 call tess-ui built-ins (`format_date`, `current_date`: pass them as `functions=`); 1 is a nested dict literal cut at its first `}}` by my own regex, i.e. the TDL slot-end rule |
| `if:`/`for:`/`key:` texts | 172 | 171 | 1 | `date_add_days`, a tess-ui built-in |
| `handlers:` | 107 | **0** | 107 | TEL is expression-only: `open = not open`, `n = n + 1; cmd = ...`, `a(); b()` are assignments and statement sequences, which TEL refuses |

Reading: slots and conditions are practically compatible (99%, the rest needing the built-in functions registered). **Handlers are the gap.** tess-ui handlers are small statements (assign, sequence, call). Moving to TEL needs a decision: a handler language of its own on top of TEL (assignment targets plus `;`), TEL growing an assignment/sequence form, or rewriting handlers as calls to named actions on the ViewModel. This is the main design question for the switch.

## Handlers as TDL step blocks (`Set { Target, Value }`, `Call { Action, args }`), values as TEL (checked 2026-11-14)
All `handlers:` texts of the 110 shipped view and stylesheet files (113 unique event/text pairs) were parsed as Python statements and mapped to steps, then each step's value expression was compiled with `tess_el.compile_expression`.

- **113 of 113 convert**; none needs a loop, a conditional statement or anything but assignment and calls. 180 steps in all.
- **Targets are plain names in all 144 assignments** (no attribute or subscript targets), so `Target` can be a plain name.
- **0 value expressions fail in TEL** (including conditional expressions such as `x if c else y`, and `event.key == 'space'`).
- Call steps: the callee (`on_toggle`, `surface.dismiss`) is not an expression TEL evaluates; it is checked by tess-ui against the ViewModel and its built-in actions, as today. Only the arguments go to TEL.
- Not checked: how `event` and loop variables are scoped in a step's TEL expression; the order of writes inside one handler (a later step reads an earlier step's write, as in `n = n + 1; cmd = str(n)`), which needs a stated rule: each step sees the writes of the earlier ones.

## Round trip (2026-11-14), `spike/roundtrip.py`
YAML view -> TDL text (If/For wrappers, handlers as `Set`/`Call` step blocks, slots bare) -> `tess_dl.parse` and `loads` -> dict -> compared with the original dict.

- **61 of 61 shipped `*_View.yaml` come back equal** (498 widget nodes, 121 handler groups, 166 `if:`, 33 `for:`). Not vacuous: a broken handler reverse leaves 19 of 61 equal; a broken number reverse, 7 of 61.
- Normalised before comparing (the differences carry no meaning): `tesserae: 0.6` read as the string `"0.6"`; `if:`/`for:`/`key:` text with or without the `{{ }}`; handler text through `ast.unparse` (spacing only).
- This is a **data-level** round trip. The TDL is not loaded by tess-ui's real loader (still YAML); because the dict equals the YAML one, the existing loader would take it, but that was not run.
- **10 `for:` nodes use a tuple target** (`for: i, it in enumerate(items)`). TDL's `For` takes one variable. The spike keeps the original target text in a `Target:` property in the For body. A real design needs a rule (a TDL `For` with a pair, or `enumerate` handled by TEL/the runtime).
- Handler steps: 0 handlers stayed text; the `Call` callee is a string (`on_toggle`, `surface.dismiss`).
- Mixed text-and-slot strings and slots containing `}}` stay quoted strings and round-trip as data; whether the runtime then treats them as templates is unchanged from today.
- **tess_dl API gap:** `api.md` promises `Block.properties`, `Block.get`, `Block.blocks`, `Block.walk` and `Document.find`; the pinned commit has no `properties`, `get`, `blocks` or `walk` on `Block` (only `entries`, `name`, `type`, edits). The spike reads `entries`.

## Verdict
The mapping is lossless on every shipped view. What remains for the real switch is engineering, not design risk: the loader reading TDL (positions, error messages), the 49 stylesheet and theme files, the 10 tuple-`for` loops, tree-shape effects of the `If`/`For` wrappers on `part:` paths and hot reload (not exercised here), and converting tests and docs.
