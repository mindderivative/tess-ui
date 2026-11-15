# Badges

*Communication*

## In Material Design 3

A badge shows that something has news. The small one is a dot, and the large one carries a short count or
text. It sits on the corner of what it describes.

## In Tesserae

`Badge` is a view Tesserae ships (`Badge_View.tdl`) with its look as rules (`Badge_Stylesheet.tdl`): a 6 pixel `Error` dot, or with a
`Value` a 16 pixel pill in `label_small` on `on_error`, at least 16 wide and growing with its text.

A `Value` that is a number over `Limit` shows as the limit and a plus (`999+` by default), and `Show: "<| unread > 0 |>"` hides a zero count. With
`Anchored: true` the children are the host, and the badge sits over the host's top right corner.

Anchored, a dot overlaps the corner by 4 and a pill starts 12 in from the corner and 4 above it. The badge is hidden from a screen reader: put the
count in the host's label ("Inbox, 3 unread"). The parts a stylesheet can address are `mark` and `label`.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Badge { ... }`. A file of the same name in your project replaces it.

### `Badge`

The Material 3 badge: a 6 dp dot (no value) or a 16 dp pill holding a count or short text. Alone it is the mark itself, to place where you like; with `Anchored: true` its children are the host (an icon, a button, a tab) and the mark sits over the host's top right corner. The look is in Badge_Stylesheet.tdl; this file is the structure. A count over `Limit` shows as `999+`. Hide a zero count with `Show: "<| n > 0 |>"`. The mark is hidden from a screen reader: put the count in the host's label ("Inbox, 3 unread").

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Value` | `any` |  | A number or a few characters. Empty is a dot. |
| `Limit` | `int` | `999` | A number over this shows as the limit and a plus. |
| `Show` | `bool` | `true` | Whether the badge shows. |
| `Anchored` | `bool` | `false` | The children are the host, and the mark sits on its top right corner. |

Children go in the default slot.

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `host` (Container), `mark` (Container), `label` (Text).

Its look is in [`Badge_Stylesheet.tdl`](../stylesheets/badges/badge.md).

## Using it

```tdl
Container {
  Name: nav
  Style { Flex_Direction: horizontal, Gap: 24, Width: 200, Height: 60, Padding: 16 }
  Children {
    Badge {
      Value: <| unread |>
      Show: <| unread > 0 |>
      Anchored: true
      Children {
        Icon {
          Icon: email
          Style { Width: 24, Height: 24, Foreground: on_surface }
        }
      }
    }
    Badge {
      Anchored: true
      Children {
        Icon {
          Icon: home
          Style { Width: 24, Height: 24, Foreground: on_surface }
        }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import badge

unread = badge(app.window, "3")
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Badge_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Badge
    Part: mark
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
