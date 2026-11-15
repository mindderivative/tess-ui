# Slider

*Selection and input*

## In Material Design 3

A slider lets the user pick a value from a range by dragging a handle, or with the keyboard.

## In Tesserae

`Slider`, a Tesserae control: a 4 pixel track, a 20 pixel handle and a 40 pixel state layer in a 48 pixel target. A bound `Value` follows the drag, not only its end.
With a `Step` the value snaps to multiples of it from `Min`, the keys move by it (else by a hundredth of the range), and `Ticks: true` puts a mark at each step: a discrete
slider (without a `Step` there is nothing to mark). `Value_Indicator: true` shows a bubble with the value over the handle while it is dragged or has the keyboard focus.
A `Max` that is not above `Min`, or a `Step` that is not positive, is an error.

Three looks go beyond the standard one. `Vertical: true` stands it up: the bottom is `Min`, `Style.Height` is its length and `Style.Width` the touch target's. `Size`
(`xs`, `s`, `m`, `l` or `xl`) is the Expressive form: a track 16, 24, 40, 56 or 96 pixels thick, in two pieces with a 6 pixel gap either side of a thin 4 pixel handle that
stands across it. `Icon` insets a glyph at the start of the track (it needs a `Size` of `s` or larger) in the colour of what it lies on.

Events: `on_input` while it is dragged (every step), `On_Change` once it is let go, and after each key. Dragging captures the pointer, and a press anywhere on the track
sets the value there. The arrow keys step it (all four, whichever way it lies), Page Up and Down move by ten steps, Home and End go to the ends, and a screen reader can
increment, decrement and set it. The colour is `Style.Foreground` and the length is `Style.Width` (`Style.Height` when `vertical`); a slider laid out longer or shorter than
it was built, in a flexible row, takes the room it was given.

### Range slider

`RangeSlider` picks two values, a least and a most, with two handles. It takes the slider's `Min`, `Max`, `Step`, `Ticks`, `Value_Indicator`,
`vertical`, `Size`, `Icon`, `Label` and `Disabled`, and, in place of `Value`, two two-way numbers: `Low`, the least of the two, and `High`, the most. A `High` below
`Low` is read as `Low`.

The handles never cross: a drag stops at the other handle. Each handle is its own stop for Tab, has its own state layer and focus ring and, for a
screen reader, is a slider of its own (named from `Label`: "Price, minimum" and "Price, maximum"; its reach is up to or down from the other handle).
The arrow, Page Up and Down keys move the handle that has the focus; Home and End take it to the end of what it may reach. A press on the track moves the
nearer handle there, and a drag keeps hold of the handle it began on. The track between the handles is `primary`; with a `Size` it is three pieces, a gap
from each handle. `on_input` and `On_Change` fire as for a slider; read the values from the bound `Low` and `High`.

## How it is built

### `Slider`

Picks a value between `min` and `max` by dragging.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Value` | `float` |  | From `Min` to `Max`; a bound Signal follows the drag. Two-way. |
| `Min` | `float` |  |  |
| `Max` | `float` | `1.0` |  |
| `Step` | `float` |  | Snap to multiples of this from `Min`; the keys move by it. |
| `Ticks` | `bool` |  | A mark at each step (needs `Step`): a discrete slider. |
| `Value_Indicator` | `bool` |  | A bubble with the value over the handle while it is dragged or has the keyboard. |
| `Vertical` | `bool` |  | Stood up: the bottom is `Min`; `Style.Height` is its length and `Style.Width` the touch target's. |
| `Size` | `xs` or `s` or `m` or `l` or `xl` |  | MD3 Expressive's size: a thicker track in two pieces and a thin 4 px handle (empty: the standard 4 px track and 20 px handle). |
| `Icon` | `str` |  | An icon inset at the start of the track (needs a `Size` of `s` or larger). |
| `Label` | `str` |  | What a screen reader calls it. |
| `Disabled` | `bool` |  |  |

Its `Style` also takes `Foreground`.

### `RangeSlider`

Picks two values, a least and a most, between `min` and `max` by dragging two handles.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Low` | `float` |  | The least of the two values; a bound Signal follows the drag. Two-way. |
| `High` | `float` | `1.0` | The most of the two values; it is never below `Low`. Two-way. |
| `Min` | `float` |  |  |
| `Max` | `float` | `1.0` |  |
| `Step` | `float` |  | Snap to multiples of this from `Min`; the keys move by it. |
| `Ticks` | `bool` |  | A mark at each step (needs `Step`): a discrete slider. |
| `Value_Indicator` | `bool` |  | A bubble with the value over a handle while it is dragged or has the keyboard. |
| `Vertical` | `bool` |  | Stood up: the bottom is `Min`; `Style.Height` is its length and `Style.Width` the touch target's. |
| `Size` | `xs` or `s` or `m` or `l` or `xl` |  | MD3 Expressive's size: a thicker track in three pieces and thin 4 px handles (empty: the standard 4 px track and 20 px handles). |
| `Icon` | `str` |  | An icon inset at the start of the track (needs a `Size` of `s` or larger). |
| `Label` | `str` |  | What a screen reader calls it; the handles are 'minimum' and 'maximum' of it. |
| `Disabled` | `bool` |  |  |

Its `Style` also takes `Foreground`.

## Using it

```tdl
Container {
  Name: player
  Style { Flex_Direction: vertical, Gap: 16, Width: 280, Height: 160, Padding: 16 }
  Children {
    Slider {
      Value: <| volume |>
      Min: 0
      Max: 100
      Label: Volume
      Value_Indicator: true
      Style { Width: 240 }
    }
    Slider {
      Value: <| stars |>
      Min: 1
      Max: 5
      Step: 1
      Ticks: true
      Style { Width: 240 }
    }
    RangeSlider {
      Low: <| cheapest |>
      High: <| dearest |>
      Min: 0
      Max: 500
      Step: 10
      Label: Price
      Style { Width: 240 }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import slider

volume = slider(app.window, (0xFF, 0xFF, 0xFF, 0xFF), 240, 44, value=0.5)
volume.on_change(print)
```

## See also

- [Controls](../guide/controls.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
