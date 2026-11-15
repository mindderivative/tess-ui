# Spin box

*Selection and input*

## In Material Design 3

Material Design 3 has no spin box. Tesserae's is built from MD3's parts: a number field between two 40dp
icon buttons.

## In Tesserae

The `SpinBox` kind (`SpinBox` in a view), a Tesserae control: a 64 by 40 pixel number field between two 40 pixel buttons. The buttons, the up and down arrow keys in the
field and a screen reader's increment and decrement change `Value` by `Step`; typing a number sets it once it parses and fits `Min` to `Max`, and leaving the field puts the
value's text back if what was typed did not. A button whose step would pass a bound is disabled, unless `Wrap` is on (it needs `Min` and `Max`): then a step past one bound
lands on the other and the buttons never disable. `Decimals` fixes how many places show (without it, only as many as the number needs). `Prefix` and `Suffix` (a currency sign,
a unit) are shown with the number, and typing may include them or not. `Label` is the name for a screen reader.

Holding a button steps again after 400 milliseconds and then every 80, until it is let go or reaches a bound; Page Up and Page Down step ten at a time.
`SpinBoxField` is a view Tesserae ships that adds a visible `Label` above and a line of `Supporting` or `Error` text under it (`Least` and `Most` are its
bounds, `Min` and `Max` being reserved names). Not built: a hold that speeds up the longer it is held, and a spin box in a vertical arrangement.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `SpinBoxField { ... }`. A file of the same name in your project replaces it.

### `SpinBoxField`

A spin box with a visible label above it and a line of supporting or error text under it, as a text field has them. `Value` is two-way. The label also names the spin box for a screen reader; when `Error` is not empty it replaces the supporting text, in the error colour.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Label` | `str` |  | The name above the spin box. |
| `Supporting` | `str` |  | Help under it. |
| `Error` | `str` |  | An error message; it replaces the supporting text. |
| `Value` | `float` | `0` | The number; stepping and typing write it back. Two-way: give it a bare reference and the view writes it back. |
| `Least` | `float` |  | The least it takes (`Min` is a reserved name). |
| `Most` | `float` |  | The most it takes. |
| `Step` | `float` | `1` | How far a button moves it. |
| `Decimals` | `int` |  | How many decimal places show. |
| `Prefix` | `str` |  | Shown before the number. |
| `Suffix` | `str` |  | Shown after the number (a unit). |
| `Wrap` | `bool` | `false` | A step past one bound lands on the other. |
| `Disabled` | `bool` | `false` | Dimmed and not steppable. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `label` (Text), `box` (SpinBox), `help` (Text).

Its look is in [`SpinBoxField_Stylesheet.tdl`](../stylesheets/spin-boxes/spin-box-field.md).

### `SpinBox`

A number with step buttons. Holding a button repeats the step; Page Up and Page Down step by ten.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Value` | `float` |  |  Two-way. |
| `Min` | `float` |  |  |
| `Max` | `float` |  |  |
| `Step` | `float` | `1.0` |  |
| `Disabled` | `bool` |  |  |
| `Label` | `str` |  | What a screen reader calls it. |
| `Decimals` | `int` |  | How many decimal places show (empty: only as many as the number needs). |
| `Prefix` | `str` |  | Shown before the number, such as a currency sign. |
| `Suffix` | `str` |  | Shown after the number, such as a unit. |
| `Wrap` | `bool` |  | A step past one bound lands on the other (needs min and max). |

## Using it

```tdl
Container {
  Name: order
  Style { Flex_Direction: vertical, Gap: 16, Width: 320, Height: 240 }
  Children {
    SpinBox {
      Value: <| count |>
      Min: 0
      Max: 10
      Label: Count
    }
    SpinBoxField {
      Label: Weight
      Value: <| weight |>
      Least: 0
      Most: 50
      Step: 0.5
      Decimals: 1
      Suffix: " kg"
      Supporting: "Up to 50"
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import spin_box

quantity = spin_box(app.window, 1, min=0, max=10)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# SpinBoxField_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: SpinBoxField
    Part: label
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Controls](../guide/controls.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
