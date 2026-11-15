# Top app bar

*Navigation*

## In Material Design 3

A top app bar sits along the top of a screen with its title and the actions for it: a navigation icon at the
start and up to a few action icons at the end.

## In Tesserae

`TopAppBar` is a view Tesserae ships (`TopAppBar_View.tdl`): a bar as wide as its place, built from `IconButton`s and a title.

The `Variant` is `small` (64 tall, the title beside the icon, the default), `center` (64, the title in the middle), `medium` (112) or `large` (152), the last two with the title under
the icons. `Leading_Icon` is the navigation icon (`menu` or `arrow_back`), `Leading_Label` its name and tooltip, and `On_Leading` what it does. `Actions` are up to three icons at the
end, each `{Value, Icon, Label}`; pressing one sets `Chosen` to its `Value`. `Collapsed` makes a medium or large bar show as a small one (the height eases), and `Scrolled` says content
is under the bar: its colour goes from `surface` to `surface_container`. `Frosted: true` makes the surface translucent and blurred.

Bind `Collapsed` and `Scrolled` to how a list under the bar has scrolled (the `At_Top` of a `ScrollView`). Every icon is a button with a label, which is its name and its
tooltip. With `App(borderless=True)` a bar can sit in a window's title area; the title bar of a window is `TitleBar`. Not built: the contextual action mode (a selection bar
that replaces it), and a search bar inside it (`SearchBar` is its own view).

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `TopAppBar { ... }`. A file of the same name in your project replaces it.

### `TopAppBar`

The Material 3 top app bar: a navigation icon, a title and up to three action icons across the top of a screen. `Variant`: `small` (64 tall, the title beside the icon), `center` (64, the title in the middle), `medium` (112, the title under the row of icons) and `large` (152, a bigger title under them). The medium and large collapse to the small form while `Collapsed` is true (bind it to the way a list under it has scrolled), and `Scrolled` (true once content is under the bar) turns its colour from `surface` to `surface_container`. `Leading_Icon` is the navigation icon (`menu` or `arrow_back`) and its `On_Leading` handler; `Actions` is a list of {value, icon, label}, pressing one sets `Chosen` to its `Value`. Every icon has a label (its name and its tooltip). Role: a group.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Frosted` | `bool` | `false` | A translucent surface that blurs what is behind it (72% of its colour, a 20 pixel backdrop blur). |
| `Title` | `str` |  | The title. |
| `Variant` | `small` or `center` or `medium` or `large` | `small` | How tall it is and where the title sits. |
| `Leading_Icon` | `str` |  | The navigation icon (menu, arrow_back). |
| `Leading_Label` | `str` | `Navigation` | The navigation icon's name and tooltip. |
| `On_Leading` | `handler` |  | What the navigation icon does. |
| `Actions` | `list` | `[]` | Up to three icons at the end, each {value, icon, label}. |
| `Chosen` | `any` |  | The value of the action last pressed. Two-way: give it a bare reference and the view writes it back. |
| `Collapsed` | `bool` | `false` | A medium or large bar shows as a small one. |
| `Scrolled` | `bool` | `false` | Content is under the bar: its colour changes. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `row` (Container), `leading` (IconButton), `lead_space` (Container), `lead_filler` (Container), `title` (Text), `filler` (Container), `action` (IconButton), `big_title` (Text).

Its look is in [`TopAppBar_Stylesheet.tdl`](../stylesheets/top-app-bar/top-app-bar.md).

## Using it

```tdl
Container {
  Name: inbox
  Style { Flex_Direction: vertical, Width: 480, Height: 400 }
  Children {
    TopAppBar {
      Title: Inbox
      Variant: large
      Leading_Icon: menu
      On_Leading: open_drawer
      Collapsed: <| not at_top |>
      Scrolled: <| not at_top |>
      Chosen: <| command |>
      Actions {
        Item { Value: search, Icon: magnify, Label: Search }
        Item { Value: more, Icon: dots_vertical, Label: More }
      }
    }
    ScrollView {
      At_Top: <| at_top |>
      Style { Flex: fill }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import top_app_bar

bar = top_app_bar(app.window, "Notes", leading_icon="menu", trailing_icons=["settings"])
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# TopAppBar_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: TopAppBar
    Part: title
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Custom Title Bars](../guide/custom-title-bars.md)
- [Windows And Docks](../guide/windows-and-docks.md)
- [Effects](../guide/effects.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
