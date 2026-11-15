# Carousel

*Content*

## In Material Design 3

A carousel shows a row of items that scroll, with the focused one largest. MD3 has multi-browse, uncontained,
hero and full-screen layouts.

## In Tesserae

`Carousel` is a view Tesserae ships (`Carousel_View.tdl`): a `ScrollView` that scrolls sideways (`Orientation: horizontal`) and settles on an item
(`Snap`, with each item's `Snap_Align`), of items with 28 pixel corners, 8 pixels apart, with a title on a darkened band.

Each of `Items` is `{Value, Title}` and optionally `{image, Supporting}`. `Variant` sets how big the items are: `uncontained` (the default; every item `Item_Width` wide),
`multi_browse` (a large item, a medium one, then small ones), `hero` (large items with a peek of the next) or `center_hero` (the middle item large, with a peek of each
neighbour). `Width` and `Height` are the carousel's own size (360 by 200 by default). Pressing an item sets `Chosen` (two-way) to its `Value`.

The wheel and a drag scroll it; when it stops it settles with an item at the start (the middle for `center_hero`). The items are focusable and the arrow keys move along
them. A `ScrollView` takes `Snap` (`none`, `start`, `center`, `end`) and any node a `Snap_Align` style, so other strips can do the same. Not built: the sizes changing as
it scrolls (a multi-browse carousel's large item is the first one), parallax on the pictures, dot indicators, full-screen, autoplay.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Carousel { ... }`. A file of the same name in your project replaces it.

### `Carousel`

The Material 3 carousel: a row of rounded items that scrolls sideways and settles with an item lined up (the scroll view's `Snap`). `Items` is a list of {value, title} and optionally {image, supporting}; `Variant` sets how big they are: `uncontained` (every item `Item_Width` wide), `multi_browse` (a large item, a medium one, then small ones), `hero` (large items with a peek of the next) and `center_hero` (the item in the middle large, with a peek of the ones either side). `Width` and `Height` are the carousel's own. Pressing an item sets `Chosen` to its `Value`; the items are focusable and the arrows move along them. The wheel and a drag scroll it, and so do the arrows once an item is focused.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Items` | `list` | `[]` | The items, each {value, title} and optionally {image, supporting}. |
| `Variant` | `uncontained` or `multi_browse` or `hero` or `center_hero` | `uncontained` | How big the items are. |
| `Chosen` | `any` |  | The value of the item last pressed. Two-way: give it a bare reference and the view writes it back. |
| `Width` | `float` | `360` | How wide the carousel is. |
| `Height` | `float` | `200` | How tall the items are. |
| `Item_Width` | `float` | `200` | uncontained: how wide each item is. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `item` (Container), `picture` (Image), `caption` (Container), `title` (Text), `supporting` (Text).

Its look is in [`Carousel_Stylesheet.tdl`](../stylesheets/carousel/carousel.md).

## Using it

```tdl
Container {
  Name: gallery
  Style { Width: 420, Height: 260 }
  Children {
    Carousel {
      Variant: hero
      Chosen: <| opened |>
      Items {
        Item { Value: a, Title: Paris, Supporting: "Three days" }
        Item { Value: b, Title: Rome }
        Item { Value: c, Title: Lisbon }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import carousel

gallery = carousel(app.window, 480, 180, layout="multi_browse", items=[])
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Carousel_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Carousel
    Part: title
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
