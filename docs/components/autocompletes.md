# Autocomplete

*Selection*

## In Material Design 3

Material 3 has no combo box (it has the menu-based select and the search view); the baseline is the WAI-ARIA combobox with a listbox popup.

## In Tesserae

`Autocomplete` is a view Tesserae ships (`Autocomplete_View.tdl`) with a mind, the `Combobox` widget (`combobox_controls.py`), which holds the behaviour in Python so that it can be tested with no window. It is an outlined
text field with a popup list that narrows as the person types, for a closed set too long to scan. `Options` are `{value, label}` and optionally `{hint, disabled}`; matching is by containing text, case aside, in the
order of the options, with the matched letters in weight 500; `Strict` (the default) keeps the value one of the options, and `Strict: false` lets the typed text be the value. `Picked` holds the value of the option last
picked when `On_Pick` runs.

The field keeps the keyboard focus all the time and the active row is the field's `active_descendant` (the engine's property). Down opens the list with the selected row (or the first enabled one) active and then moves down,
stopping at the last; Alt+Down opens with no active row; Up opens with the last enabled row, and from the first row makes none active; Page Down and Page Up move a page; Home and End are the text's. Enter picks the active
row (with none: Strict puts the value back, Free takes the text); Escape closes the list and keeps the text, and with the list closed Strict puts the value back; Tab (the field losing the focus) picks the row an arrow key chose,
else the option whose label the text is (case aside), else Strict puts the value back and Free keeps the text. A press on a row picks it. The list shows eight rows (a row is a menu row high: 40, 32, 28, with a hint 56, 48, 40),
scrolls, and the popup is as wide as the field, 160 to 360. "No matches" shows when nothing matches.

Not built: inline completion, the chevron and clear buttons, row templates (swatch, icon, font sample), the count announcement, and the 40 dp field at `default` (it is the Text Field's own height there). The tess-behavior
combobox cases (SPEC 2.5d) are not adapted yet.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Autocomplete { ... }`. A file of the same name in your project replaces it.

### `Autocomplete`

The combo box (ux spec Autocomplete; the WAI-ARIA combobox with a listbox popup): an outlined text field with a popup list of options that narrows as the person types, for a closed set too long to scan (the Role of a block, a token). `Options` is a list of {value, label} and optionally {hint, disabled}; matching is by containing text, case aside, in the order of the options, and the matched letters are in weight 500. The field keeps the keyboard focus all the time: Down opens the list and moves the active row (Alt+Down opens without one), Up the other way, Enter picks the active row, Escape closes the list and then puts the value back, Tab picks an option whose label the text is (or the row an arrow key chose) and otherwise puts the value back. `Strict: false` is the free form: the typed text may be the value. The list shows eight rows and scrolls; the popup is as wide as the field (at least 160, at most 360). Not built: inline completion, the chevron and clear buttons, row templates (swatch, icon, font sample), the count announcement.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Options` | `list` | `[]` | The options, each {value, label} and optionally {hint, disabled}. |
| `Value` | `any` |  | The value of the chosen option; a pick writes it (Free: the text taken as the value). Two-way: give it a bare reference and the view writes it back. |
| `Picked` | `any` |  | The value of the option last picked, written before `On_Pick` is called: bind it to a name the caller reads in its `On_Pick`. Two-way: give it a bare reference and the view writes it back. |
| `Label` | `str` |  | What is being chosen: the accessible name of the field and the list (the form row beside it shows the visible label). |
| `Placeholder` | `str` | `"Type to search"` | Shown in the empty field. |
| `Strict` | `bool` | `true` | true: the value is always one of the options; false: the typed text may be the value. |
| `Disabled` | `bool` | `false` | Dimmed and does not take the focus. |
| `On_Pick` | `handler` |  | Called after an option has been picked or a free text taken (`Value` holds it). |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `mind` (Combobox), `field_box` (Container), `field` (TextField), `layer` (Overlay), `surface` (Container), `list_box` (Container), `list` (VirtualList), `row` (Container), `texts` (Container), `row_label` (Text), `row_hint` (Text), `check` (Icon), `empty` (Text).

Its look is in [`Autocomplete_Stylesheet.tdl`](../stylesheets/autocompletes/autocomplete.md).

### `Combobox`

The combo box's mind: it draws nothing. It holds the options, the text, the list and the active row, does what the keys and the leaving of the field mean (Strict and Free), and tells the view through the names it is bound to.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Value` | `any` |  | The value of the chosen option (Free: the text taken as the value). A pick writes it. Two-way. |
| `Text` | `str` |  | The text in the field: the view's field writes it as the person types, and a pick or a revert writes the label. Two-way. |
| `Expanded` | `bool` |  | Whether the list is open: it opens on typing and on Down, and the popup writes false when Escape or a press outside closes it. Two-way. |
| `Options` | `list` | `[]` | The options, each {value, label} and optionally {hint, disabled}. |
| `Strict` | `bool` | `true` | True: the value is always one of the options and leaving the field puts the last value back; false: the typed text may be the value. |
| `Rows` | `int` | `8` | How many rows show at once (for Page Up and Page Down and for scrolling the active row into view). |
| `Row_Height` | `float` | `32.0` | How tall a row is, in pixels. |
| `Command` | `str` |  | What to do, written as text that starts with a number that is new each time (`7 key arrow_down`): `key arrow_down`, `key arrow_down alt`, `key enter`, `leave` (the field lost the focus), `click 2`, `Toggle`. |
| `Scroll` | `float` |  | The list's scroll offset: bind the list's `Scroll_Offset` to the same name; moving the active row writes the offset that shows it. Two-way. |
| `Entries` | `list` |  | Output: written to the name it is bound to. The options that match the text, each {value, label, hint, disabled, runs, selected}: `Runs` is the label with the matched part in weight 500. Two-way. |
| `Active` | `int` |  | Output: written to the name it is bound to. The place of the active row among `Entries`, or -1 when there is none. Two-way. |
| `Count` | `int` |  | Output: written to the name it is bound to. How many options match. Two-way. |
| `Disabled` | `bool` |  |  |

## Using it

```tdl
Container {
  Name: panel
  Style { Width: 360, Height: 200, Padding: 16 }
  Children {
    Autocomplete {
      Label: Fruit
      Value: banana
      Options {
        Item { Value: apple, Label: Apple }
        Item { Value: avocado, Label: Avocado, Hint: "Green" }
        Item { Value: banana, Label: Banana }
      }
    }
  }
}
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Autocomplete_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Autocomplete
    Part: surface
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Overlays](../guide/overlays.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
