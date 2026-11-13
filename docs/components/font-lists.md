# Font list

*Selection and input*

## In Material Design 3

Material Design 3 has no font picker: an app's type is chosen by its designers. An app whose people pick a typeface for something (a launcher, a terminal, a block of a configuration)
needs one, and it is built from what MD3 does describe: an outlined text field for the search and a list of selectable rows on a menu-like surface.

## In Tesserae

Two views and one control. `FontList` is the view you use: the list inline, or (`popup: true`) a 48 pixel button that shows the family, in its own face, and opens the list in a layer under it.
`FontListPanel` is the inside of it, with no surface and no button. `FontBrowser` is the control that draws nothing and is the list's mind (`tess_ui.font_controls`): the families, the search and the cursor,
which the view reaches through the names it binds to it.

The families come from `tess_ui.font_families`: by default `fc-list : family`, a read-only subprocess given five seconds, whose lines are split on newlines and commas (each line holds a family and its names
in other languages), trimmed, de-duplicated (a name that differs only in case is the same family) and sorted without regard to case. It runs once, when the first list is built, and the answer is
kept (`font_families.refresh()` asks again). `font_families.use(provider)` swaps the source: `provider()` returns the names or raises `FontListError`, which a test or an app that knows its fonts uses.
The list is the families installed on the machine: the faces the engine ships (`Roboto`, `Noto Sans Arabic`, `Hack Nerd Font Mono`) are in it only where the machine has them too. A machine with no `fc-list`,
or one where it fails, takes more than five seconds or lists nothing has no list: the view shows an outlined text field for the family's name, with the reason under it, in place of the search, the list
and (with `popup`) the button and the layer.

A row is the family's name, drawn in that family when the engine can draw it (a family `tess_ui.fonts.available_families()` knows: the bundled ones and any registered with `register_font`) and in the ordinary
face when it cannot, since the engine does not look for system fonts. `value` is two-way text: the family's name. A value that is not an installed family is kept as it is and nothing is selected. The search
field keeps the families whose name has every word typed, in any order, without regard to case; a name that starts with the first word comes first. The list is a `VirtualList` of `rows` rows (8 by default): it
builds the rows in view and three past each edge, however many families there are (seven thousand open at once), and opens scrolled so that `value` shows, with the cursor on it.

The keyboard. The search field has the focus when a popup opens: Up, Down, Page Up and Page Down move the cursor in the list and Enter picks the family under it (Left, Right, Home, End and Space are the text's).
Tab goes on to the list, where Up and Down move by a row, Page Up and Page Down by `rows`, Home and End go to the ends, and Enter and Space pick. A press picks too. A pick writes `value`, calls `on_change`
and closes a popup unless `close_on_pick` is false. Escape and a press outside close a popup (writing false to `open`), and the focus goes back to the button. A screen reader hears a group named by `label`,
a `list` of `listitem`s each named by its family and `selected` when it is the value, the search field, a button that says "label: family" and is `expanded` while the layer is open, and an alert for a search
that finds nothing.

The look is in `FontList_Stylesheet.yaml` and `FontListPanel_Stylesheet.yaml`: write one in your project to change the button, the layer and the rows. Not built: a sample sentence in each row, favourites or
recently used families, grouping by foundry or script, weights and styles of a family, and system fonts the engine cannot draw (they are listed, in the ordinary face).

## How it is built

A view Tesserae ships is a `<Name>_View.yaml` (what it takes and what it is made of) with a `<Name>_Stylesheet.yaml` (how it looks). Use it by name: `widget: FontList`. A file of the same name in your project replaces it.

### `FontList`

The font list: a searchable list of the installed font families, each in its own face where the engine can draw it, either inline or (`popup: true`) behind a button that shows the family (in its own face) and opens the list in a layer under it. The families come from `tess_ui.font_families` (`fc-list : family`, once; swap the source with `font_families.use`). `value` is two-way: the family's name. Escape and a press outside close the popup (writing false to `open`); a pick closes it too, unless `close_on_pick` is false. When the installed families cannot be listed there is a text field in place of the list (and of the button). `on_change` is called after each pick. What the list does is in FontListPanel.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | `str` |  | The font family. Two-way: give it a bare reference and the view writes it back. |
| `popup` | `bool` | `false` | Show a button with the family that opens the list in a layer, instead of the list itself. |
| `open` | `bool` | `false` | A popup list: whether it is showing; Escape, a pick and a press outside write false. Two-way: give it a bare reference and the view writes it back. |
| `close_on_pick` | `bool` | `true` | A popup list closes when a family is picked. |
| `rows` | `int`, 3 to 16 | `8` | How many rows show at once. |
| `width` | `float`, 160 to 640 | `280` | How wide the list is. |
| `label` | `str` | `Font` | What a screen reader calls the list and the button that opens it. |
| `placeholder` | `str` | `Choose a font` | What the button says while there is no family. |
| `disabled` | `bool` | `false` | Dimmed and not editable; a popup does not open. |
| `on_change` | `handler` |  | Called after each pick. |

Its parts, by name (a stylesheet rule's `part:` or `name:` addresses one): `swatch` (FontBrowser), `free` (TextField), `field` (Container), `trigger_text` (Text), `trigger_chevron` (Icon), `trigger` (Container), `layer` (Overlay), `surface` (Container), `popup_panel` (FontListPanel), `panel` (FontListPanel).

Its look is in [`FontList_Stylesheet.yaml`](../stylesheets/font-lists/font-list.md).

### `FontListPanel`

The inside of a font list, with no surface and no button: a search field over a list of the installed font families, each shown in its own face when the engine can draw it (and in the ordinary one when it cannot). `value` is two-way: the family's name. A press picks a family; in the list the Up and Down arrows, Page Up, Page Down, Home and End move the cursor and Enter or Space pick it; in the search field Up, Down, Page Up and Page Down move the cursor in the list and Enter picks it. The list is a `VirtualList` that builds the rows in view and a few past them. When the installed families cannot be listed (a machine with no `fc-list`), there is no list: a text field takes the family's name, and says why. `on_change` is called after each pick. Nothing is listed until `open` is true. What the parts do is in the FontBrowser control (`tess_ui.font_controls`), which this view drives by writing a numbered command to `cmd`.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | `str` |  | The font family. Two-way: give it a bare reference and the view writes it back. |
| `rows` | `int`, 3 to 16 | `8` | How many rows show at once. |
| `width` | `float`, 160 to 640 | `280` | How wide it is. |
| `open` | `bool` | `true` | Whether the list is built and answers; a popup's panel is open while the popup shows. |
| `label` | `str` | `Font` | What a screen reader calls the list, and the text field that stands in for it. |
| `disabled` | `bool` | `false` | Dimmed and not editable. |
| `on_change` | `handler` |  | Called after each pick. |

Its parts, by name (a stylesheet rule's `part:` or `name:` addresses one): `browser` (FontBrowser), `free` (TextField), `search` (TextField), `list_group` (Container), `list_box` (Container), `list` (VirtualList), `row` (Container), `row_name` (Text), `empty` (Text).

Its look is in [`FontListPanel_Stylesheet.yaml`](../stylesheets/font-lists/font-list-panel.md).

### `FontBrowser`

The font list's mind: it draws nothing. It asks `tess_ui.font_families` for the installed families, searches them, keeps the cursor and tells the view through the names it is bound to.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | `str` |  | The font family: a pick writes it. Two-way. |
| `open` | `bool` | `true` | Whether the list is built: going true makes it; nothing is listed before. `mode` and `current` are kept either way. |
| `query` | `str` |  | The search text: a family is kept when its name has every word of it, without regard to case. |
| `rows` | `int` | `8` | How many rows show at once (for Page Up and Page Down and for scrolling the cursor into view). |
| `row_height` | `float` | `40.0` | How tall a row is, in pixels. |
| `command` | `str` |  | What to do, written as text that starts with a number that is new each time (`7 key arrow_down`): `key arrow_down`, `key arrow_up field` (from the search field), `click Fira Sans`. |
| `scroll` | `float` |  | The list's scroll offset: bind the list's `scroll_offset` to the same name; moving the cursor writes the offset that shows it. Two-way. |
| `entries` | `list` |  | Output: written to the name it is bound to. The families that match the search, each {family, loadable}: `loadable` says the engine can draw text in that family. Two-way. |
| `cursor_name` | `str` |  | Output: written to the name it is bound to. The family the keyboard is on, or empty. Two-way. |
| `count` | `int` |  | Output: written to the name it is bound to. How many families the search found. Two-way. |
| `mode` | `str` |  | Output: written to the name it is bound to. Empty until it has asked for the families, then `list`, or `text` when they cannot be listed (no `fc-list`, or it failed): the view then offers a text field. Two-way. |
| `message` | `str` |  | Output: written to the name it is bound to. Why the families cannot be listed; empty when they can. Two-way. |
| `current` | `any` |  | Output: written to the name it is bound to. The row of `value`: {family, loadable}, for the button of a closed popup. Two-way. |
| `disabled` | `bool` |  |  |

## Using it

```yaml
name: terminal
widget: Container
style: {flex_direction: vertical, gap: 16, width: 480, height: 560, padding: 16}
children:
  - {widget: FontList, popup: true, open: "{{ choosing }}", value: "{{ family }}", label: Terminal font, on_change: font_changed}
  - {widget: FontList, value: "{{ family }}", rows: 6, width: 320}
```

## Using it in Python

```python
from tess_ui import font_families

# the default asks `fc-list : family` once; an app that knows where its fonts are can say so
font_families.use(lambda: ["Alegreya", "Fira Code", "Hack Nerd Font Mono"])
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.yaml` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `style:` beats every rule:

```yaml
# FontList_Stylesheet.yaml, or any stylesheet your app loads
styles:
  - widget: FontList
    part: surface
    style: {background: tertiary}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Controls](../guide/controls.md)
- [Icon Pickers](../components/icon-pickers.md)
- [Python API reference](../api/python.md)
- [YAML reference](../api/yaml.md)
