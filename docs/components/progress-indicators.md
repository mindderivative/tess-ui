# Progress indicators

*Communication*

## In Material Design 3

Progress indicators show that something is happening. **Determinate** ones fill as a value from 0 to 1
grows; **indeterminate** ones keep moving when there's no value to show. The loading indicator is MD3's
shape-morphing one, for short waits.

## In Tesserae

Each is a Tesserae control (`tess_ui.controls`), not a drawing of `tess_re`'s: `LinearProgress`, `CircularProgress` and
`LoadingIndicator`. Leave `Value` out, or let an expression give nothing, for a wait with no end; a number from 0 to 1 is determinate and
eases to each new value.

A bar is 240 pixels long and 4 thick, and a ring is 48 across, unless the call's `Style:` gives a `Width`; the colour is `Style.Foreground`, `primary` by default. A bar
has a `surface_container_highest` track behind it and a ring has none, until `Track` names a colour role; a stop dot at the end of the bar's track is opt-in
(`Stop_Indicator`), as is a `Buffer` (how much has loaded, 0 to 1, a lighter bar behind the value). With a `Track`, a determinate ring and its track are a gap apart
(4 pixels between the rounded ends), as in MD3. A `Wavy` bar is taller than its `Thickness` by the wave's height (6 pixels), and a wavy ring's arc is a wave round
a plain track. A screen reader hears a progress bar with its value as a percentage, or as busy when there is none. An app that reduces motion gets a still bar and arc
instead of the endless motion. The two bars of `Two_Bar` keep their widths as they cross, so the sweep approximates MD3's, whose bars grow and shrink; the wave's size
and speed and the thicker sizes are written from memory of the spec and have not been checked against it.

## How it is built

### `LinearProgress`

A progress bar.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Value` | `float` |  | 0 to 1; leave out, or give nothing, for a wait with no end. |
| `Track` | `str` |  | The colour role of the track behind the indicator. |
| `Thickness` | `float` |  | The bar's height in pixels (4 is the standard one; MD3 Expressive's are thicker). |
| `Buffer` | `float` |  | 0 to 1: how much has loaded, drawn as a lighter bar behind the value. |
| `Stop_Indicator` | `bool` |  | A dot at the end of the track (Material 3). |
| `Wavy` | `bool` |  | The bar is a sine wave that flows along a straight track (MD3 Expressive); the control is taller by the wave's height. |
| `Two_Bar` | `bool` |  | A wait with no end sweeps as two bars, a long one and a short one a little behind (MD3), not one. |
| `Label` | `str` |  | What a screen reader calls it. |

Its `Style` also takes `Foreground`.

### `CircularProgress`

A progress ring.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Value` | `float` |  | 0 to 1; leave out, or give nothing, for a wait with no end. |
| `Track` | `str` |  | The colour role of the track behind the indicator. |
| `Wavy` | `bool` |  | The arc is a wave whose crests flow round the ring (MD3 Expressive). |
| `Thickness` | `float` |  | The ring's width in pixels (4 is the standard one; MD3 Expressive's are thicker). With a `Track` the arc and the track are a gap apart. |
| `Label` | `str` |  | What a screen reader calls it. |

Its `Style` also takes `Foreground`.

### `LoadingIndicator`

An indeterminate wait indicator.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Contained` | `bool` |  | The shape in a `primary_container` circle, in `on_primary_container` (MD3 Expressive). |
| `Label` | `str` |  | What a screen reader calls it. |

Its `Style` also takes `Foreground`.

## Using it

```tdl
Container {
  Name: upload
  Style { Flex_Direction: vertical, Gap: 16, Width: 280, Height: 140, Padding: 16 }
  Children {
    LinearProgress {
      Value: <| sent |>
      Buffer: <| queued |>
      Label: Uploading
      Style { Width: 240 }
    }
    LinearProgress {  # no value: a wait with no end
      Style { Width: 240 }
    }
    CircularProgress {
      Value: <| sent |>
      Track: secondary_container
    }
    LinearProgress {
      Value: <| sent |>
      Wavy: true
      Thickness: 4
      Style { Width: 240 }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import linear_progress

upload = linear_progress(app.window, 240, value=0.4)
upload.value.set(0.8)
```

## See also

- [Controls](../guide/controls.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
