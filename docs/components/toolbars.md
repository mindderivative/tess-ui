# Toolbars

*Navigation*

## In Material Design 3

A toolbar groups the actions for the content around it. A **docked** one is fixed to an edge; a **floating**
one is a rounded bar over the content.

## In Tesserae

`Toolbar` is a view Tesserae ships (`Toolbar_View.tdl`): one widget for the docked and the floating toolbar, built from `IconButton`s, an optional `Fab` and a `Menu`.

A `docked` toolbar spans its width (or `Width`), 64 tall, on `surface_container`; a `floating` one is a pill with a shadow as long as its buttons, and with `Orientation: vertical` a
column 64 wide. `Vibrant: true` puts it on `primary_container`, with `on_primary_container` icons. The `Items` are icon buttons, each `{Value, Icon, Label}` and optionally `Disabled`;
the `Value` of the item or overflow row pressed goes to `Chosen`. `Overflow` is `Menu` rows under a more button at the end. `Fab_Icon` (with `Fab_Label` and `On_Fab`) adds a small
action button at the end. With `Fit`, items that do not fit move, in order, into the overflow menu; a docked toolbar measures itself, a floating one uses `Max_Length` pixels.
`Hidden` fades it out and takes its buttons out of the tab order (bind it to the way a list scrolls). `Label` is its accessible name, and `Disabled` stops every button.

Your own content goes in the default slot after the items. The arrow keys move between the buttons (one Tab stop). The role is `Group`: the engine has no toolbar role.
With `Fit`, the items that spill and the rows of `Overflow` share one menu, a divider between. Not built: sliding out of the way (it fades).

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Toolbar { ... }`. A file of the same name in your project replaces it.

### `Toolbar`

The Material 3 toolbar: a row (or, floating, a column) of icon buttons with an optional action button at the end and an overflow menu. `Variant: docked` spans its width, 64 tall, on `surface_container`; `floating` is a pill with a shadow that is as long as its buttons, and `Vibrant: true` puts it on `primary_container` (the icons on_primary_container). `Items` is a list of {value, icon, label} and optionally {disabled}: pressing one sets `Chosen` to its `Value`; every icon has a label (its name and its tooltip). `Overflow` is a list of Menu rows shown under a more button at the end; with `Fit: true` the items that do not fit go there by themselves. Your own content goes in the default slot after the items. `Fab_Icon` (with `Fab_Label` and `On_Fab`) adds an action button at the end. `Hidden: true` fades the toolbar out of the way and out of the tab order (bind it to the way a list scrolls). The arrow keys move between the buttons (one Tab stop). Role: a group, because the engine has no toolbar role.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Variant` | `docked` or `floating` | `docked` | docked spans its width; floating is a pill with a shadow. |
| `Orientation` | `horizontal` or `vertical` | `horizontal` | A row, or (for the floating one) a column. |
| `Vibrant` | `bool` | `false` | primary_container, with on_primary_container icons. |
| `Width` | `any` |  | A docked toolbar's width; the width of its place when not given. |
| `Label` | `str` | `Toolbar` | The toolbar's accessible name. |
| `Items` | `list` | `[]` | The icon buttons, each {value, icon, label} and optionally {disabled}. |
| `Overflow` | `list` | `[]` | Menu rows under a more button at the end (empty shows no button). |
| `Chosen` | `any` |  | The value of the item or overflow row last pressed. Two-way: give it a bare reference and the view writes it back. |
| `Fab_Icon` | `str` |  | An action button at the end (empty shows none). |
| `Fab_Label` | `str` |  | Its name and tooltip. |
| `On_Fab` | `handler` |  | What the action button does. |
| `Fit` | `bool` | `false` | Items that do not fit move into the overflow menu, after the ones that do (a docked toolbar measures itself; a floating one uses `Max_Length`). |
| `Max_Length` | `any` |  | A floating toolbar's longest length in pixels, for `Fit`. |
| `Hidden` | `bool` | `false` | Faded out of the way and out of the tab order. |
| `Disabled` | `bool` | `false` | No button responds. |
| `Bare` | `bool` | `false` | No items and no group: only the bar, for a Python widget that adds its own nodes straight into it. |

Children go in the default slot.

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `group` (Container), `item` (IconButton), `more` (IconButton), `menu` (Menu), `fab` (Fab).

Its look is in [`Toolbar_Stylesheet.tdl`](../stylesheets/toolbars/toolbar.md).

## Using it

```tdl
Container {
  Name: editor
  Style { Width: 420, Height: 200, Padding: 16, Flex_Direction: vertical, Gap: 16 }
  Children {
    Toolbar {
      Name: tools
      Items {
        Item { Value: bold, Icon: format_bold, Label: Bold }
        Item { Value: italic, Icon: format_italic, Label: Italic }
        Item { Value: link, Icon: link, Label: Link }
      }
      Overflow {
        Item { Value: copy, Label: Copy }
        Item { Value: share, Label: Share }
      }
      Fab_Icon: plus
      Fab_Label: Add
      Chosen: <| last |>
    }
    Toolbar {
      Variant: floating
      Vibrant: true
      Items {
        Item { Value: search, Icon: search, Label: Search }
        Item { Value: star, Icon: star, Label: Star }
      }
    }
    Text {
      Text: <| last |>
      Typography_Role: body_medium
      Style { Foreground: on_surface }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import toolbar

tools = toolbar(app.window, variant="floating", width=240)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Toolbar_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Toolbar
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
