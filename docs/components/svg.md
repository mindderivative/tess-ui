# SVG

*Content*

## In Material Design 3

Material Design 3 uses SVG for its icons and illustrations. An SVG document is vector art: shapes, gradients,
patterns, clips, masks and text, which scale to any size without blurring.

## In Tesserae

`Svg`: the engine parses and draws the whole document as one scene, scaled to fit the node's box and
centred in it. Tesserae reads the file, and decodes the raster pictures in it (`<image href="...">`: PNG, JPEG, GIF
or WebP, found next to the SVG file, or a `data:` URL) for the engine, which decodes no image format. `Style.Foreground` is what
`currentColor` means in the document, so a monochrome icon follows the theme, light and dark. Give a `Width` or a
`Height`, or both.

Give one of `Src`, a `.svg` or `.svgz` file next to the view (an expression, so it follows a Signal), and `Content`, the document itself as text. `Alt` says what the picture
shows, for a screen reader; without it the picture is decorative and hidden from one, unless it handles clicks. A missing file, or a document that is not SVG, stops the view
opening with the widget's name in the message.

## How it is built

### `Svg`

A vector picture.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Src` | `str` |  | A .svg or .svgz file, relative to the view. |
| `Content` | `str` |  | The SVG text, instead of a file. |
| `Alt` | `str` |  | What the picture shows, for a screen reader. Without it the picture is decorative and hidden from one. |

Its `Style` also takes `Foreground`.

## Using it

```tdl
Container {
  Name: brand
  Style { Flex_Direction: vertical, Gap: 16, Width: 240, Height: 160 }
  Children {
    Svg {
      Src: logo.svg
      Alt: "The Tesserae logo"
      Style { Width: 96, Height: 96, Foreground: primary }
    }
    Svg {
      Content: "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\"><circle cx=\"12\" cy=\"12\" r=\"10\" fill=\"currentColor\"/></svg>"
      Style { Width: 24, Height: 24, Foreground: on_surface }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import svg

logo = svg(app.window, '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><circle cx="12" cy="12" r="10" fill="currentColor"/></svg>',
           width=48, height=48, color="primary", label="A dot")
```

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
