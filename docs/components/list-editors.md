# List editor

*Selection and input*

## In Material Design 3

Material Design 3 has no editor for a list of values. An app whose people keep a list (the words of a launcher's filter, the outputs of a layout, the colours of a palette) needs one, and it is built from what MD3
does describe: a column of rows, each with a field of its own kind and icon buttons to move and remove it, and a button that adds.

## In Tesserae

Two views and one control. `ListEditor` is the view you use. `ListEditorRow` is one of its rows, and `ListModel` is the control that draws nothing and is the editor's mind (`tess_ui.list_controls`: the items,
the edits and the identity of each item, which the view reaches through the names it binds to it).

`value` is a Python list, two-way. `item_kind` says what every item is, and each row has the widget of that kind: `text` an outlined text field, `number` a spin box (bounded by `least` and `most`, stepped by `step`;
a whole number stays an `int` when the step is whole, else it is a `float`), `bool` a switch, `enum` a button that shows the item's label and opens a menu of `choices` (plain values, or `{value, label}`) and `colour`
a swatch that opens the colour picker in a popup (`'#rrggbb'` or `'#rrggbbaa'` text). A row also has Move up, Move down and Remove buttons (the first row cannot move up, the last cannot move down), and the Add
button under the rows appends an item of the kind: empty text, the least number (or 0), false, the first choice, black. `min_items` stops Remove (and says why under the list), `max_items` (0 is no limit)
stops Add; an empty list says "No items".

Writing. A text row writes when Enter is pressed or the field is left, never per key; a spin box, a switch, a menu and a colour picker write when they change. An edit writes a new list in which only the edited item differs,
and `on_change` is called after it. A list the app sets is shown as it is and never rewritten: an item that does not fit the kind (`"x"` among numbers, a choice that is not one, a colour that is not one) is
shown as the kind's nearest value (0, the first choice, black) and left exactly as it was until the person edits that row. Each item has an identity of its own that stays with it when it is moved, so a row keeps
what is in it (a field being typed in, an open menu) when other rows move or go, and a list the app sets has new rows. Turning a list into text and back (a TDL list `[a, b, c]`) is not the editor's job.

The keyboard. Tab goes through each row's field or button, then Move up, Move down and Remove, and on to the next row and the Add button; Enter or Space press a button, the arrows are the spin box's and the menu's,
Escape closes a menu or a colour popup. A screen reader hears a group named by `label`, a `list` of `listitem`s named by it and their place (`Shortcuts 2`), each widget with the same name, and buttons that say
"Move up", "Move down", "Remove" and the Add button's label; the message under the list is an alert. A disabled editor edits nothing. The look is in `ListEditor_Stylesheet.yaml` (the empty note and the message); the
rows' widgets look as their own do. Not built: dragging a row to move it, Alt+arrow keys to move one (a handler cannot yet choose between three calls by the key), items of mixed kinds, and items that are themselves lists.

## How it is built

A view Tesserae ships is a `<Name>_View.yaml` (what it takes and what it is made of) with a `<Name>_Stylesheet.yaml` (how it looks). Use it by name: `widget: ListEditor`. A file of the same name in your project replaces it.

### `ListEditor`

A list editor: the items of a list as rows, each with the widget of the item kind (`item_kind`: `text` a text field, `number` a spin box bounded by `least` and `most`, `bool` a switch, `enum` a button that opens a menu of `choices`, `colour` a colour picker in a popup), and buttons to move a row up or down and to remove it, and an Add button that appends an item of the kind (empty text, the least number or 0, false, the first choice, black). `value` is the list and is two-way: an edit writes a new list in which only the edited item differs, and `on_change` is called after each edit the person makes; a list the app sets is shown as it is, with new rows, and never rewritten. `min_items` and `max_items` bound the length. The keyboard: Tab goes through each row's widget and buttons, Enter or Space press a button. Turning a list into TDL text and back is not its job. What the parts do is in the ListModel control (`tess_ui.list_controls`), which this view drives by writing a numbered command to `cmd`.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | `list` | `[]` | The list: its items are all of `item_kind`. Two-way: give it a bare reference and the view writes it back. |
| `item_kind` | `text` or `number` or `bool` or `enum` or `colour` | `text` | The kind of every item. |
| `choices` | `list` | `[]` | An enum's choices: plain values, or {value, label}. |
| `least` | `float` |  | A number's least. |
| `most` | `float` |  | A number's most. |
| `step` | `float` | `1` | A number's step; whole numbers stay ints when it is whole. |
| `min_items` | `int`, 0 or more | `0` | The fewest items: the remove buttons stop at it. |
| `max_items` | `int`, 0 or more | `0` | The most items (0 for no limit): the Add button stops at it. |
| `label` | `str` | `Items` | What a screen reader calls the list; an item is called by it and its place. |
| `add_label` | `str` | `Add` | The Add button's label. |
| `disabled` | `bool` | `false` | Dimmed and not editable. |
| `on_change` | `handler` |  | Called after each edit the person makes. |

Its parts, by name (a stylesheet rule's `part:` or `name:` addresses one): `model` (ListModel), `rows` (Container), `item` (ListEditorRow), `empty` (Text), `message_text` (Text), `actions` (Container), `add` (Button).

Its look is in [`ListEditor_Stylesheet.yaml`](../stylesheets/list-editors/list-editor.md).

### `ListEditorRow`

One row of a list editor: the widget of the item kind (a text field, a spin box, a switch, a button that opens a menu of choices, or a colour picker in a popup) and the buttons that move the row up and down and remove it. It does not hold the list: when the person changes the item it writes the new value to `typed` (a number, `true` or `false`, or a choice as text) and calls `on_commit`, which is the list editor's to answer. A text field commits on Enter and when it is left, the others when they change. The row keeps what the person has typed and not yet committed, which is why the list editor gives each item a row of its own that follows it when it moves.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `kind` | `text` or `number` or `bool` or `enum` or `colour` | `text` | The kind of the item: which widget the row has. |
| `item` | `any` |  | The item, as its kind has it (it seeds what the row shows; a change the app makes is a new row). |
| `options` | `list` | `[]` | An enum's choices, as {value, label}. |
| `least` | `float` |  | A number's least. |
| `most` | `float` |  | A number's most. |
| `step` | `float` | `1` | A number's step. |
| `label` | `str` | `Item` | What a screen reader calls the item. |
| `position` | `int` | `1` | The row's place in the list, from 1, for a screen reader. |
| `first` | `bool` | `false` | The first row: it cannot move up. |
| `last` | `bool` | `false` | The last row: it cannot move down. |
| `can_remove` | `bool` | `true` | Whether the remove button works. |
| `disabled` | `bool` | `false` | Dimmed and not editable. |
| `typed` | `any` |  | Written when the item is changed: its new value as text. Two-way: give it a bare reference and the view writes it back. |
| `on_commit` | `handler` |  | Called after `typed` has been written. |
| `on_up` | `handler` |  | Called by the move up button. |
| `on_down` | `handler` |  | Called by the move down button. |
| `on_remove` | `handler` |  | Called by the remove button. |

Its parts, by name (a stylesheet rule's `part:` or `name:` addresses one): `cell` (Container), `text` (TextField), `number` (SpinBox), `flag` (Switch), `choice` (Button), `choices` (Menu), `colour` (ColourPicker), `up` (IconButton), `down` (IconButton), `remove` (IconButton).

### `ListModel`

The list editor's mind: it draws nothing. It holds the items of one kind, does the edits a row sends as commands, and tells the view through the names it is bound to.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | `list` | `[]` | The list. An edit writes a new list in which only the edited item differs; a list the app sets is never normalised. Two-way. |
| `item_kind` | `str` | `text` | The kind of every item: `text`, `number`, `bool`, `enum` or `colour`. |
| `choices` | `list` | `[]` | An `enum`'s choices: plain values, or {value, label}. |
| `least` | `float` |  | A `number`'s least. |
| `most` | `float` |  | A `number`'s most. |
| `step` | `float` |  | A `number`'s step; a whole number stays an int when the step is one. |
| `min_items` | `int` |  | The fewest items: `remove` does nothing at it. |
| `max_items` | `int` |  | The most items (0 for no limit): `add` does nothing at it. |
| `command` | `str` |  | What to do, written as text that starts with a number that is new each time (`7 key arrow_down`): `set 2 new text` (item 2 is now that text; a number, `true` or `false`, a choice's value or a colour as its text), `add`, `remove 2`, `up 2`, `down 2`. |
| `rows` | `list` |  | Output: written to the name it is bound to. The items as {uid, value}: the uid stays with an item when it is moved, and the value is as the item kind has it. Two-way. |
| `options` | `list` |  | Output: written to the name it is bound to. An `enum`'s choices as {value, label}. Two-way. |
| `count` | `int` |  | Output: written to the name it is bound to. How many items. Two-way. |
| `can_add` | `bool` |  | Output: written to the name it is bound to. Whether `add` would add. Two-way. |
| `can_remove` | `bool` |  | Output: written to the name it is bound to. Whether `remove` would remove. Two-way. |
| `message` | `str` |  | Output: written to the name it is bound to. Why the last edit did nothing (the list is at its fewest, or `item_kind` is not a kind); empty when nothing is wrong. Two-way. |
| `disabled` | `bool` |  |  |

## Using it

```yaml
name: launcher
widget: Container
style: {flex_direction: vertical, gap: 16, width: 520, height: 420, padding: 16}
children:
  - {widget: ListEditor, value: "{{ words }}", label: Filter words, add_label: Add word, on_change: words_changed}
  - {widget: ListEditor, value: "{{ levels }}", item_kind: enum, choices: [{value: low, label: Low}, {value: high, label: High}], max_items: 4}
  - {widget: ListEditor, value: "{{ sizes }}", item_kind: number, least: 0, most: 64}
```

## Using it in Python

```python
from tess_ui.list_controls import ListModel

model = ListModel("number", [1, 2, 3], least=0, most=10)
model.set(1, "50")        # a row sends the new item as text: 2 becomes 10
model.move(2, -1)         # the item keeps its identity: [1, 3, 10]
model.values              # [1, 3, 10]
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.yaml` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `style:` beats every rule:

```yaml
# ListEditor_Stylesheet.yaml, or any stylesheet your app loads
styles:
  - widget: ListEditor
    part: empty
    style: {foreground: tertiary}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Controls](../guide/controls.md)
- [Spin Boxes](../components/spin-boxes.md)
- [Colour Pickers](../components/colour-pickers.md)
- [Python API reference](../api/python.md)
- [YAML reference](../api/yaml.md)
