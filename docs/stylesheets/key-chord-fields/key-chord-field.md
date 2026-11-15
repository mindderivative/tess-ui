# KeyChordField_Stylesheet.tdl

The look of KeyChordField: the record button is 56 pixels tall (the height of the field beside it) with 12 pixel corners and 16 pixels of padding, a 1 pixel `outline` border, and `primary_container` while it is recording. It has the state layer, ripple and focus ring of any pressable node, and a disabled one fades to 38%.

The look of [`KeyChordField`](../../components/key-chord-fields.md) (in [Key chord field](../../components/key-chord-fields.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: KeyChordField
Tesserae: "0.6"
---
# The look of KeyChordField: the record button is 56 pixels tall (the height of the field beside it) with 12 pixel corners and 16 pixels of padding, a 1 pixel `outline` border, and `primary_container`
# while it is recording. It has the state layer, ripple and focus ring of any pressable node, and a disabled one fades to 38%.
Styles {
  Rule {
    Widget: KeyChordField
    Part: record
    Style { Corner_Radius: 12, Border_Width: 1, Border_Color: outline, Padding { Left: 16, Right: 16, Top: 0, Bottom: 0 } }
  }
}
```

## How it reaches the view

Each rule names `Widget: KeyChordField` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `record` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Corner_Radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Border_Width` | `1` | The width of its border, in pixels. |
| always | `Border_Color` | `outline` | The colour of its border: a colour or a gradient. |
| always | `Padding` | `{ Left: 16, Right: 16, Top: 0, Bottom: 0 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: KeyChordField
    Part: record
    Style { Corner_Radius: tertiary }
  }
}
```
