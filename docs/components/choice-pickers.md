# Choice pickers

*Selection*

## In Material Design 3

Material 3 has the menu used as a select (Material Web `md-outlined-select`): an outlined button that shows the current choice and opens a menu of the options under it.

## In Tesserae

`ChoicePicker` is a view Tesserae ships (`ChoicePicker_View.tdl`): an outlined button and a `Menu` of the `Options` under it, an anchored popup. `Options` are `{value, label}` and optionally
`{hint, disabled}`; a `hint` is a line of explanation under the label (a menu row takes it too: `Hint` on `MenuItem`), the row of the current `Value` is checked, and a disabled row is skipped
by the keys. A pick writes `Value` (and `Picked`, for a caller that gives `Value` as an expression and reads the choice in its `On_Pick`). The button is as high as a control of the density (40, 32, 28);
`Hug` makes it as wide as its longest label, at least 56 pixels (a length's unit beside its number), otherwise it takes the width of its place.

Down, Up, Enter and Space on the button open the menu with its first row in focus (a press opens it with none); Escape closes it and the focus is on the button; the rows take the arrow keys, Home, End and
typing the start of a label. The button is named by `Label` and says whether it is expanded. Not built: the filter field over about 12 options (an Autocomplete is the control for those), the dialog form
below 600 dp, and the `haspopup` flag (the engine has no such property yet). The command chooser (a choice made for a command, with no button) is a `Menu` the application opens under a node it names.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `ChoicePicker { ... }`. A file of the same name in your project replaces it.

### `ChoicePicker`

The choice picker (ux spec Choice Picker): an outlined button that shows the current choice of a closed set, and opens a `Menu` of the options under it (an anchored popup, not a dialog). `Options` is a list of {value, label} and optionally {hint, disabled}: a `Hint` is a line of explanation under the label; the row of the current value is checked. Pressing a row writes its `Value` to `Value` and calls `On_Pick`. Down, Up, Enter and Space on the button open the menu with the first row in focus; Escape closes it and the focus is on the button; the rows take the arrow keys, Home, End and typing the start of a label. `Hug: true` makes the button as wide as its longest label (a length's unit beside a number field, at least 56 pixels); otherwise it takes the width of its place. The button is as tall as a control of the density (40, 32, 28). Not built: the filter field over about 12 options (use an Autocomplete), the dialog form below 600 dp and `haspopup` (the engine has no such property yet).

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Options` | `list` | `[]` | The choices, each {value, label} and optionally {hint, disabled}. |
| `Value` | `any` |  | The value of the chosen option: a pick writes it (a caller that gives an expression keeps its own copy until the expression changes). Two-way: give it a bare reference and the view writes it back. |
| `Picked` | `any` |  | The value of the row last pressed, written before `On_Pick` is called: bind it to a name the caller reads in its `On_Pick`. Two-way: give it a bare reference and the view writes it back. |
| `Label` | `str` |  | What is being chosen: the button's accessible name. |
| `Placeholder` | `str` | `Choose` | Shown while no option has the value. |
| `Hug` | `bool` | `false` | As wide as the longest label (at least 56 pixels) instead of the width of its place. |
| `Disabled` | `bool` | `false` | Dimmed and does not open. |
| `On_Pick` | `handler` |  | Called after a row has been chosen (`Value` holds it). |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `button` (Container), `shown` (Text), `chevron` (Icon), `menu` (Menu).

Its look is in [`ChoicePicker_Stylesheet.tdl`](../stylesheets/choice-pickers/choice-picker.md).

## Using it

```tdl
Container {
  Name: panel
  Style { Width: 360, Height: 160, Padding: 16 }
  Children {
    ChoicePicker {
      Label: Edge
      Value: <| edge |>
      Options {
        Item { Value: top, Label: TOP, Hint: "The top edge of the screen" }
        Item { Value: bottom, Label: BOTTOM }
      }
    }
  }
}
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# ChoicePicker_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: ChoicePicker
    Part: chevron
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Overlays](../guide/overlays.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
