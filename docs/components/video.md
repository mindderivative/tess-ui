# Video

*Content*

## In Material Design 3

Video is content, not a component, in Material Design 3; Tesserae shows frames you supply.

## In Tesserae

An `Image` takes a `Frame`, `(rgba bytes, width, height)`, from a binding and shows each new one; it keeps the last when the binding gives nothing. There is no decoder: the app decodes and pushes.

`VideoPlayer` is a view Tesserae ships (`VideoPlayer_View.tdl`) that puts transport controls under such a picture: a play/pause button, the time, a seek slider, the length and a mute button.

The app pushes each `Frame` as the video plays; `Width` and `Height` are the picture's size (the controls are as wide) and `Fit` how it fills its box (`contain` here). The three
two-way values are `Playing` (the play button flips it; the app's player follows), `Position` (seconds; the seek slider shows and writes it, and the app moves it on as it plays)
and `Muted` (the volume button flips it). `Duration` is the length in seconds, and the slider is off without one. `Buffering` lays a wait ring over the picture, `Caption` puts a
subtitle on a darkened band at its foot, `Step` is how far the arrow keys move the slider, and `Label` is the player's name for a screen reader.

On the seek slider: Space plays or pauses, the arrows step the position, M mutes. Not built: a decoder (decode with the library you choose, and set `Frame`), full-screen, speeds, a volume level, a poster.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `VideoPlayer { ... }`. A file of the same name in your project replaces it.

### `VideoPlayer`

A video player: a picture surface with the usual transport controls under it. Tesserae has no decoder, so the app supplies the frames: a `Frame` (rgba bytes, width, height) that a ViewModel updates as it plays, like an `Image`'s `Frame`. The player owns none of the playing: `Playing` (two-way) is what the play button flips, `Position` (two-way, seconds) is where the seek slider is and what it writes when dragged, and the app's player follows both and moves `Position` on as the video plays. `Duration` is the length in seconds. `Muted` (two-way) is the volume button. `Buffering` lays a wait ring over the picture; `Caption` is a line of subtitle on a darkened band at its foot. Keys, on the seek slider: Space plays or pauses, the arrows step `Position` by `Step` seconds, M mutes (the buttons are Tab stops with their own keys). The role is a group named by `Label`. Not here: a decoder, full-screen, speeds, a volume level.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Frame` | `any` |  | The current picture: (rgba bytes, width, height), pushed by the app as the video plays. |
| `Width` | `float` | `480` | The picture's width. |
| `Height` | `float` | `270` | The picture's height. |
| `Fit` | `cover` or `contain` or `fill` | `contain` | How the picture fills its box. |
| `Playing` | `bool` | `false` | Whether it is playing; the play button flips it. Two-way: give it a bare reference and the view writes it back. |
| `Position` | `float` | `0` | Seconds in; the seek slider shows and writes it. Two-way: give it a bare reference and the view writes it back. |
| `Duration` | `float` | `0` | The length in seconds. |
| `Muted` | `bool` | `false` | Whether the sound is off; the volume button flips it. Two-way: give it a bare reference and the view writes it back. |
| `Buffering` | `bool` | `false` | A wait ring over the picture. |
| `Caption` | `str` |  | A subtitle line shown at the foot of the picture. |
| `Step` | `float` | `1` | Seconds the arrow keys move the seek slider (and a drag lands on a multiple of it). |
| `Label` | `str` | `Video` | What a screen reader calls the player. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `stage` (Container), `picture` (Image), `wait` (CircularProgress), `caption` (Container), `caption_text` (Text), `controls` (Container), `play` (IconButton), `elapsed` (Text), `seek` (Slider), `total` (Text), `volume` (IconButton).

Its look is in [`VideoPlayer_Stylesheet.tdl`](../stylesheets/video/video-player.md).

## Using it

```tdl
Container {
  Name: movie
  Style { Width: 520, Height: 320, Padding: 16 }
  Children {
    VideoPlayer {
      Frame: <| frame |>
      Playing: <| playing |>
      Position: <| position |>
      Duration: 125
      Muted: <| muted |>
      Caption: <| words |>
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import video

clip = video(app.window, 320, 180, fit="contain")
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# VideoPlayer_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: VideoPlayer
    Part: elapsed
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
