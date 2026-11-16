# Images

*Content*

## In Material Design 3

An image shows a picture, fitted to its box. Material Design 3 describes how to crop and round it in a
container: a corner from the shape scale, a circle for an avatar.

## In Tesserae

`Image` is the engine's picture node: Tesserae reads and decodes the file (PNG, JPEG, GIF or WebP, turned upright by its EXIF orientation), and `Fit` says how it fills the box (`cover` by default, or `contain` or `fill`).
`Src` is relative to the view, and can be an expression, so it follows a Signal. `Alt` says what the picture shows, for a screen reader; without it the picture is decorative
and hidden from one, unless it handles clicks. The path must be relative and stay inside the view's directory; an absolute one, or one that leaves it, is refused.

Its shape is `Style.Corner_Radius`: a number, a shape token, `full` for a circle on a square picture, or a different radius on each
corner (`{top_left: 24}`). The engine clips the picture to it: `full` on a square picture is a circle (an avatar), and on any other a pill. Put it in a rule
(`Classes: [avatar]`) and every picture with the class takes the shape. Not built: a picture clipped to any other shape (the engine can mask a node with a circle, a rounded rectangle or a path, but no style passes one on).
A missing or unreadable file stops the view opening, with the widget's name and the file in the message.

## How it is built

### `Image`

A picture.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Src` | `str` |  | A path relative to the file. |
| `Fit` | `cover` or `contain` or `fill` | `cover` | How the picture fills its box. |
| `Alt` | `str` |  | What the picture shows, for a screen reader. Without it the picture is decorative and hidden from one. |
| `Frame` | `any` |  | A video frame, (rgba, width, height), pushed from a ViewModel. |

## Using it

```tdl
Container {
  Name: profile
  Style { Flex_Direction: vertical, Gap: 16, Width: 240, Height: 320 }
  Children {
    Image {
      Src: cat.png
      Alt: "A grey cat asleep on a windowsill"
      Fit: cover
      Style { Width: 240, Height: 160, Corner_Radius: medium }
    }
    Image {
      Src: avatar.png
      Alt: "Your photo"
      Style { Width: 64, Height: 64, Corner_Radius: full }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import image

photo = image(app.window, "cat.png", 200, 150, fit="cover")
```

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
