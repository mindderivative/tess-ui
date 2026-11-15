# Navigation rail

*Navigation*

## In Material Design 3

A navigation rail puts three to seven destinations in a narrow column beside the content, on medium and
large windows. Each is an icon in a pill with a label; the selected one's pill is filled.

## In Tesserae

Four views Tesserae ships: `NavigationRail` (the column), `NavigationRailItem` (one destination), `NavigationRailScreens` (a rail whose destinations are the
app's screens) and `NavigationRailScreen` (one such destination).

The `Items` of a `NavigationRail` are `{Value, Label, Icon}` and optionally `{Badge, Disabled}` (`Badge: true` is a dot), and `Selected` is the value of the chosen one: a press, or an
arrow key, writes it back. Those of a `NavigationRailScreens` are `{Screen, Label, Icon}` and optionally `{Badge}`. The rail is 80 pixels wide with the labels under the icons, or 220
with `Expanded: true` and the labels beside them; `Alignment` puts the destinations at the `top` (the default), `center` or `bottom` of the column, and `Frosted: true` makes the
surface translucent and blurred.

A destination is a 24 pixel icon in a 56 by 32 pill (`secondary_container` when it is the chosen one) over a `label_medium` label, 12 pixels from the
next, starting 44 pixels down. Children with `Slot: header` (a menu button, a FAB) go above the destinations and `Slot: footer` below. There is one Tab stop;
the up and down arrows move the focus and choose the destination. A screen reader hears a link named by the label, the current one marked as the page.
The screens rail follows `app.current_screen` and a press is `navigate_to(screen)`; it belongs in each screen (or in a window's shell). Not built: the
modal expanded rail, sections with headings, the pill growing as it is selected (it fades in), and a `navigation` role for the rail (tess_re has none, so it is a `Group` named Navigation).

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `NavigationRail { ... }`. A file of the same name in your project replaces it.

### `NavigationRail`

The Material 3 navigation rail: a column of 3 to 7 destinations, 80 pixels wide (220 when `Expanded`, with the labels beside the icons). `Items` is a list of {value, label, icon, badge}; `Selected` is the value of the chosen one and a press writes it back. A `header` slot above the items holds a menu button or a FAB (children with `Slot: header`), a `footer` slot below them. `Alignment` groups the destinations at the top (the default), centre or bottom. One Tab stop; the up and down arrows move the focus and choose the destination.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Frosted` | `bool` | `false` | A translucent surface that blurs what is behind it (72% of its colour, a 20 pixel backdrop blur). |
| `Items` | `list` | `[]` | The destinations, each {value, label, icon} and optionally {badge, disabled}. |
| `Selected` | `any` |  | The value of the chosen destination; a press writes it back. Two-way: give it a bare reference and the view writes it back. |
| `Expanded` | `bool` | `false` | 220 pixels wide, with the labels beside the icons. |
| `Alignment` | `top` or `center` or `bottom` | `top` | Where the destinations sit in the column. |

Children go in the `header` slot, the `footer` slot.

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `destinations` (Container), `item` (NavigationRailItem).

Its look is in [`NavigationRail_Stylesheet.tdl`](../stylesheets/navigation-rail/navigation-rail.md).

### `NavigationRailItem`

One destination of a navigation rail: an icon in a 56 by 32 pill with its label under it (or, in an expanded rail, a 56 high pill with the label beside the icon). A selected item has a `secondary_container` pill; a `Badge` sits on the icon. A screen reader hears a link named by the label, current when it is selected. `Handlers: {On_Click: ...}` on the call is what a press does.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Icon` | `str` |  | The icon. |
| `Label` | `str` |  | The destination's name. |
| `Selected` | `bool` | `false` | Whether this is where the user is. |
| `Badge` | `any` |  | A count or text on the icon; empty for none, and `true` for a dot. |
| `Expanded` | `bool` | `false` | The label beside the icon, as in an expanded rail. |
| `Disabled` | `bool` | `false` | Dimmed and not pressable. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `pill` (Container), `badged` (Badge), `badged_icon` (Icon), `icon` (Icon), `inline_label` (Text), `label` (Text).

Its look is in [`NavigationRailItem_Stylesheet.tdl`](../stylesheets/navigation-rail/navigation-rail-item.md).

### `NavigationRailScreens`

A navigation rail whose destinations are the app's screens: `Items` is a list of {screen, label, icon} and optionally {badge}. The destination of the screen showing is selected, and pressing one navigates to its screen. The up and down arrows move the focus along the rail.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Items` | `list` | `[]` | The destinations, each {screen, label, icon} and optionally {badge}. |
| `Expanded` | `bool` | `false` | 220 pixels wide, with the labels beside the icons. |
| `Alignment` | `top` or `center` or `bottom` | `top` | Where the destinations sit in the column. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `item` (NavigationRailScreen).

### `NavigationRailScreen`

One destination of a navigation rail that goes to a screen of the app (Tesserae's, not Material 3's): a `NavigationRailItem` that is selected while its `Screen` is the app's current one, and whose press is `navigate_to(screen)`. The view needs an App, which is what holds the screens.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Screen` | `str` |  | The name of the screen it goes to. |
| `Label` | `str` |  | The destination's name. |
| `Icon` | `str` |  | The icon. |
| `Badge` | `any` |  | A count or text on the icon. |
| `Expanded` | `bool` | `false` | The label beside the icon. |

## Using it

```tdl
Container {
  Name: shell
  Style { Flex_Direction: horizontal, Width: 480, Height: 400 }
  Children {
    NavigationRail {
      Selected: <| page |>
      Items {
        Item { Value: home, Label: Home, Icon: home }
        Item { Value: search, Label: Search, Icon: search, Badge: 3 }
      }
    }
    NavigationRailScreens {
      Items {
        Item { Screen: Main, Label: Tasks, Icon: home }
        Item { Screen: Settings, Label: Settings, Icon: settings }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import navigation_rail

rail = navigation_rail(app.window, ["Home", "Search"], ["home", "search"], selected=0)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# NavigationRail_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: NavigationRail
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Windows And Docks](../guide/windows-and-docks.md)
- [Effects](../guide/effects.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
