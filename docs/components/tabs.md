# Tabs

*Navigation*

## In Material Design 3

Tabs organise content at one level of hierarchy, with the selected tab marked by an indicator. Primary tabs
may carry an icon above the label.

## In Tesserae

`Tabs` is a view Tesserae ships (`Tabs_View.tdl`): a row of equal tabs over a divider, with an indicator under the chosen tab that
slides to the next one.

The `Tabs` are `{Value, Label}` and optionally `{Icon, Badge}`; an expression follows its Signals. `Selected` is the value of the chosen tab, and a press or an arrow key writes it
back. With `Variant: primary` (the default) the indicator is 3 pixels tall, rounded on top, and 12 pixels in from each side of the tab; with `secondary` it is 2 pixels tall across
the whole tab. Every tab is `Tab_Width` wide (120 by default).

The bar is 48 pixels tall, or 64 when a primary bar has an icon. The chosen tab's label and icon are `primary`, the others `on_surface_variant`. The bar
is a `tablist` with one Tab stop; the arrow keys, Home and End move the focus and choose the tab. The panel each tab shows is yours: put an
`If: "selected == 'trips'"` on it. Not built: a bar that scrolls when the tabs do not fit.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Tabs { ... }`. A file of the same name in your project replaces it.

### `Tabs`

The Material 3 tab bar: a row of tabs over a divider, an indicator under the selected one that slides to the next. `Tabs` is a list of {value, label, icon, badge}; `Selected` is the chosen value and a press writes it back. `Variant: primary` (48 tall, 64 with icons, a 3 dp indicator as wide as the label's share of the tab) or `secondary` (48 tall, a 2 dp indicator across the whole tab). The tabs are `Tab_Width` wide each: a fixed bar. Arrow keys move the focus along the bar and choose the tab (one Tab stop); the panel each tab shows is yours to switch on `Selected`.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Tabs` | `list` | `[]` | The tabs, each {value, label} and optionally {icon, badge}. |
| `Selected` | `any` |  | The value of the chosen tab; a press writes it back. Two-way: give it a bare reference and the view writes it back. |
| `Variant` | `primary` or `secondary` | `primary` | primary has a short rounded indicator; secondary one across the tab. |
| `Tab_Width` | `float` | `120` | How wide each tab is. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `bar` (Container), `tab` (Container), `badged` (Badge), `badged_icon` (Icon), `icon` (Icon), `label` (Text), `indicator` (Container), `divider` (Divider).

## Using it

```tdl
Container {
  Name: trips
  Style { Flex_Direction: vertical, Width: 360, Height: 160 }
  Children {
    Tabs {
      Selected: <| tab |>
      Tabs {
        Item { Value: flights, Label: Flights, Icon: home }
        Item { Value: trips, Label: Trips, Icon: search, Badge: 3 }
        Item { Value: explore, Label: Explore, Icon: menu }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import tabs

bar = tabs(app.window, ["Videos", "Photos"], selected=0)
```

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
