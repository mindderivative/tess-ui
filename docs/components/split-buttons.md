# Split buttons

*Actions*

## In Material Design 3

A split button joins a main action to a menu of related ones: the leading part does the usual thing, and the
trailing chevron opens the others.

## In Tesserae

`SplitButton` is a view Tesserae ships (`SplitButton_View.tdl`): two `Button`s 2 pixels apart and a `Menu` for the trailing one. One widget covers all five types.

The main part has the `Label` and an optional `Icon` and runs `On_Click`; the trailing part opens a `Menu` of `Items` (rows as `Menu` takes them), and the `Value`
of the row pressed goes to `Chosen`. `Variant` and `Size` are `Button`'s and both parts take them.

The inner corners are small (4 pixels) and the outer ones round; while the menu is open the trailing part is round on every corner and its chevron is turned over. Each part is its
own Tab stop; the trailing part says it is expanded while its menu shows. Arrow-down on either part opens the menu and moves the focus to its first row (a press opens it
without moving the focus). Not built: a toggle form.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `SplitButton { ... }`. A file of the same name in your project replaces it.

### `SplitButton`

The Material 3 split button: a main action and, 2 pixels beside it, a menu button whose chevron turns over while its menu is open. `Variant` and `Size` are Button's (filled, tonal, elevated, outlined, text; xs to xl). The main part has a `Label` and an optional `Icon` and calls `On_Click`; the trailing part opens a `Menu` of `Items` ({value, label} and the rest of Menu's rows) and pressing a row sets `Chosen`. The inner corners are small and the outer ones round, and the trailing part is round on both sides while its menu is open. Tab reaches both parts; Enter or Space on either does what pressing it does.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Label` | `str` |  | The main action's text. |
| `Icon` | `str` |  | A leading icon in the main part. |
| `Variant` | `filled` or `tonal` or `elevated` or `outlined` or `text` | `filled` | Passed to both parts. |
| `Size` | `xs` or `s` or `m` or `l` or `xl` | `s` | Passed to both parts. |
| `Items` | `list` | `[]` | The menu's rows, as Menu takes them. |
| `Chosen` | `any` |  | The value of the menu row last pressed. Two-way: give it a bare reference and the view writes it back. |
| `On_Click` | `handler` |  | What the main part does. |
| `Disabled` | `bool` | `false` | Both parts are dimmed and do not respond. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `main` (Button), `trailing` (Button), `menu` (Menu).

## Using it

```tdl
Container {
  Name: compose
  Style { Width: 420, Height: 240, Padding: 16 }
  Children {
    SplitButton {
      Label: Send
      Icon: send
      On_Click: send_now
      Chosen: <| when |>
      Items {
        Item { Value: later, Label: "Send later" }
        Item { Value: draft, Label: "Save as draft" }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import split_button

send = split_button(app.window, "Send", 160, 40, variant="filled")
```

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
