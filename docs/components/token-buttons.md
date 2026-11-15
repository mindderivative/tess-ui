# Token button

*Selection and input*

## In Material Design 3

Material Design 3 has no control for choosing a design token. An app whose people point a setting at a token of the theme (`$color.primary`, `$space.md`) needs one, and it is built from what MD3 does
describe: an outlined button that shows the choice, and a searchable list of rows on a menu-like surface.

## In Tesserae

One view and one control. `TokenButton` is the view you use: a 48 pixel button that shows the token it holds and opens the list of tokens in a layer under it. `TokenList` is the control that draws nothing and is the
list's mind (`tess_ui.token_controls`: the tokens as rows, the search and the cursor, which the view reaches through the names it binds to it).

The tokens are data you give it, not read from anywhere. `Tokens` is a list of `{Name, ref, Kind, Value, doc}`: `Name` is what a person looks for (`color.primary`), `ref` is the text a pick writes
(`$color.primary`; a `$` and the name when it is left out), `Kind` says what the value is, `Value` is the token's value and `doc` one line about it. `Groups` is more tokens in named sets,
`[{Name, Tokens}]`, which come after `Tokens`; each row then says its group before its doc. `Preferred` is a list of names or refs to list first, in that order. A token with no name, or with the ref of
an earlier one, is left out. Nothing here knows what a token is: a colour kind is `colour` or `color`, and any other kind is shown as text.

A row is the token's name, a line under it with its group and doc, and its value: a swatch of the colour for a colour token whose value is `'#rrggbb'` or `'#rrggbbaa'` text, the value as text for any other
(a colour token whose value is not such text shows the text). The button shows the ref in `Value` with a swatch when the token is a colour it knows; a ref that is none of the tokens is shown as it is and
is kept. `Value` is two-way text: a pick writes the token's `ref`, calls `On_Pick` and closes the layer unless `Close_On_Pick` is false. The search keeps the tokens that have every word typed in their name,
ref, group or doc, in any order and without regard to case; a name that starts with the first word comes first, and the preferred ones stay first among equals. The search is empty each time the list opens, and
the list opens scrolled so that the held token shows, with the cursor on it. The list is a `VirtualList` of `Rows` rows (7 by default) and builds only the rows in view and three past each edge, however
many tokens there are.

The keyboard. Enter on the button, or Down, opens the layer with the search field focused. Up, Down, Page Up and Page Down in the field move the cursor and Enter picks the token under it (Left, Right, Home,
End and Space are the text's). Tab goes on to the list, where Up and Down move by a row, Page Up and Page Down by `Rows`, Home and End go to the ends, and Enter and Space pick. A press picks too. Escape and a
press outside close the layer (writing false to `Open`), and the focus goes back to the button. A screen reader hears a button named "label: ref" that is `Expanded` while the layer is open, a group, the
search field, a `list` of `listitem`s each named "name: value" and `Selected` when it is the token held, and an alert for a search that finds nothing.

The look is in `TokenButton_Stylesheet.tdl`: write one in your project to change the button, the layer and the rows. Not built: a tree of the tokens by their dotted names, tokens that are aliases of
others (an alias is a token whose value is another ref, shown as text), a preview for kinds other than colour (a spacing bar, a font sample), and reading the tokens from the theme or from the Shell's
schema (the app passes them).

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `TokenButton { ... }`. A file of the same name in your project replaces it.

### `TokenButton`

The token button: a button that shows the theme token it holds (its ref, such as `$color.primary`, with a swatch when the token is a colour the view knows) and opens a list of tokens in a layer under it. The tokens are data you give it (`Tokens`: each {name, ref, kind, value, doc}; `Groups`: more in named sets, each {name, tokens}), and `Preferred` names are listed first. A row is the token's name, a line under it with its group and doc, and its value: a swatch for a colour token (`Kind: colour` with a `'#rrggbb'` or `'#rrggbbaa'` value), the value as text for any other. The search keeps the tokens that have every word typed in their name, ref, group or doc. `Value` is two-way text: a pick writes the token's `ref` and calls `On_Pick`, and closes the layer unless `Close_On_Pick` is false. Enter or Space on the button, or Down, opens the layer with the search field focused; Up and Down in the field move the cursor and Enter picks; Tab goes on to the list, where the arrows, Page Up, Page Down, Home and End move and Enter or Space pick. Escape and a press outside close it (writing false to `Open`), and the focus goes back to the button. What the list does is in the TokenList control (`tess_ui.token_controls`), which this view drives by writing a numbered command to `cmd`.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Value` | `str` |  | The token's ref, such as `$color.primary`. A ref that is none of the tokens is kept and shown as it is. Two-way: give it a bare reference and the view writes it back. |
| `Tokens` | `list` | `[]` | The tokens, each {name, ref, kind, value, doc}: `ref` is what a pick writes (`$` and the name when left out), `Kind: colour` draws a `'#rrggbb'` or `'#rrggbbaa'` value as a swatch, `doc` is a line about it. |
| `Groups` | `list` | `[]` | More tokens in named sets, each {name, tokens}: they come after `Tokens` and each row says its group. |
| `Preferred` | `list` | `[]` | Names (or refs) of tokens to list first, in this order. |
| `Open` | `bool` | `false` | Whether the list is showing; Escape, a pick and a press outside write false. Two-way: give it a bare reference and the view writes it back. |
| `Close_On_Pick` | `bool` | `true` | The list closes when a token is picked. |
| `Rows` | `int`, 3 to 12 | `7` | How many rows show at once. |
| `Width` | `float`, 240 to 640 | `360` | How wide the list is. |
| `Label` | `str` | `Token` | What a screen reader calls the button and the list. |
| `Placeholder` | `str` | `"Choose a token"` | What the button says while there is no token. |
| `Disabled` | `bool` | `false` | Dimmed and not editable; the list does not open. |
| `On_Pick` | `handler` |  | Called after each pick. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `mind` (TokenList), `field` (Container), `current_swatch` (Container), `trigger_text` (Text), `trigger_chevron` (Icon), `trigger` (Container), `layer` (Overlay), `surface` (Container), `search` (TextField), `list_box` (Container), `list` (VirtualList), `row` (Container), `swatch` (Container), `texts` (Container), `row_name` (Text), `row_detail` (Text), `row_value` (Text), `empty` (Text).

Its look is in [`TokenButton_Stylesheet.tdl`](../stylesheets/token-buttons/token-button.md).

### `TokenList`

The token button's mind: it draws nothing. It takes the tokens as data, searches them, keeps the cursor and tells the view through the names it is bound to.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Value` | `str` |  | The ref of the token, such as `$color.primary`: a pick writes it. A ref that is none of the tokens is kept as it is. Two-way. |
| `Tokens` | `list` | `[]` | The tokens, each {name, ref, kind, value, doc}: `ref` is what a pick writes (`$` and the name when left out), `Kind` is `colour` for a colour (its `Value` is then drawn as a swatch when it is `'#rrggbb'` or `'#rrggbbaa'` text), `doc` a line about it. |
| `Groups` | `list` | `[]` | More tokens in named sets, each {name, tokens}: they follow `Tokens`, and each token is told its group. |
| `Preferred` | `list` | `[]` | Names (or refs) of tokens to list first, in this order. |
| `Open` | `bool` | `true` | Whether the list is built and answers; the current token is kept either way. |
| `Query` | `str` |  | The search text: a token is kept when its name, ref, group or doc has every word of it, without regard to case. The view's search field writes it; the control empties it each time the list opens. Two-way. |
| `Rows` | `int` | `7` | How many rows show at once (for Page Up and Page Down and for scrolling the cursor into view). |
| `Row_Height` | `float` | `56.0` | How tall a row is, in pixels. |
| `Command` | `str` |  | What to do, written as text that starts with a number that is new each time (`7 key arrow_down`): `key arrow_down`, `key arrow_up field` (from the search field), `click $color.primary`. |
| `Scroll` | `float` |  | The list's scroll offset: bind the list's `Scroll_Offset` to the same name; moving the cursor writes the offset that shows it. Two-way. |
| `Entries` | `list` |  | Output: written to the name it is bound to. The tokens that match the search, each {ref, name, kind, value, shown, doc, group, detail, swatch, label}: `swatch` is a colour token's colour as text (empty for any other), `shown` the value as text, `detail` the group and the doc. Two-way. |
| `Cursor_Ref` | `str` |  | Output: written to the name it is bound to. The ref of the token the keyboard is on, or empty. Two-way. |
| `Count` | `int` |  | Output: written to the name it is bound to. How many tokens the search found. Two-way. |
| `Current` | `any` |  | Output: written to the name it is bound to. The token of `Value`: {ref, name, kind, swatch, shown, known}, for the button of a closed popup; `known` is false when `Value` is none of the tokens. Two-way. |
| `Disabled` | `bool` |  |  |

## Using it

```tdl
Container {
  Name: accent
  Style { Flex_Direction: vertical, Gap: 16, Width: 480, Height: 640, Padding: 16 }
  Children {
    TokenButton {
      Label: Accent
      Tokens: <| tokens |>
      Preferred: ["$color.primary"]
      Value: <| accent |>
      On_Pick: accent_picked
    }
    TokenButton {
      Label: Gap
      Tokens: <| tokens |>
      Value: <| gap |>
      Open: <| choosing |>
    }
  }
}
```

## Using it in Python

```python
from tess_ui.token_controls import TokenList

tokens = [
    {"name": "color.primary", "ref": "$color.primary", "kind": "colour", "value": "#6750a4", "doc": "The brand colour"},
    {"name": "space.md", "ref": "$space.md", "kind": "dimension", "value": 16, "doc": "A medium gap"},
]
found = TokenList(tokens, preferred=["space.md"])
found.set_query("brand")                  # name, ref, group or doc, every word, any case
[row["ref"] for row in found.results]     # ['$color.primary']
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# TokenButton_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: TokenButton
    Part: surface
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Controls](../guide/controls.md)
- [Colour Pickers](../components/colour-pickers.md)
- [Font Lists](../components/font-lists.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
