# Menus

*Navigation*

## In Material Design 3

A menu shows a list of choices on a temporary surface, opened by a button, a right click or a keyboard
shortcut.

## In Tesserae

Two views Tesserae ships: `Menu`, an anchored `Overlay` holding the rows, and `MenuItem`, one 48 pixel row.

A `Menu` is shown while `Open` is true; Escape and a press outside write `false` back. `Anchor` is the name of the node in the calling view it sits against, and `Placement`
(`below` by default, `above`, `start` or `end`) the side, which it flips or shifts to fit. The `Items` are rows `{Value, Label}` and optionally `{icon, shortcut, checked, disabled,
submenu}`, `{divider: true}` for a line and `{heading: Text}` for a small heading. Pressing an item writes its `value` to `chosen`, closes the menu and calls `on_pick`. With `mode:
check` pressing an item flips its check (the checked values are `checks`); with `mode: radio` one item is checked (`selected`). The menu is `width` wide, 112 to 280 pixels (200 by
default), and `Frosted: true` makes the surface translucent and blurred.

A `MenuItem` has a `Label`, an `Icon`, `Trailing_Text` (a shortcut), `Checked` (true shows a check, false keeps the room, empty is not checkable), `Submenu` (a chevron) and
`Disabled`. An item with a `Submenu` list opens another `Menu` beside it, on a press or the Right arrow, and choosing in it closes both. The arrows move between rows,
Enter chooses, typing the start of a label jumps to it. A long press can open it (`Handlers { On_Long_Press: ... }` on the node, writing `Open`), and in Python `attach_context(node)`
on a `menu(...)` opens it at the pointer on a right-click. Not built: a right-click opener in a view, and the exposed dropdown under a text field.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Menu { ... }`. A file of the same name in your project replaces it.

### `Menu`

The Material 3 menu: a list of choices on a temporary surface next to the node it comes from (`Anchor`, the name of a node in the view that has the menu). `Items` is a list of {value, label} and optionally {icon, shortcut, checked, disabled, submenu}; a {divider: true} is a line and a {heading: "Text"} a small heading. Pressing an item sets `Chosen` to its `Value` and closes the menu; `Mode: check` makes pressing an item flip its check (kept in `Checks`, the list of checked values) and `Mode: radio` keeps one checked (`Selected`). An item with a `Submenu` list opens another menu beside it (with Right, or a press). Escape and a press outside close it (writing false to `Open`); the arrows move, Enter chooses, typing the start of a label jumps to it.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Frosted` | `bool` | `false` | A translucent surface that blurs what is behind it (72% of its colour, a 20 pixel backdrop blur). |
| `Open` | `bool` | `false` | Whether the menu is showing; Escape and a press outside write false. Two-way: give it a bare reference and the view writes it back. |
| `Anchor` | `str` |  | The name of the node in the calling view the menu sits against. |
| `Items` | `list` | `[]` | The rows: {value, label} and optionally {icon, shortcut, checked, disabled, submenu}; {divider: true}; {heading: Text}. |
| `Chosen` | `any` |  | The value of the item last pressed. Two-way: give it a bare reference and the view writes it back. |
| `Mode` | `plain` or `check` or `radio` | `plain` | plain: actions; check: items flip their checks; radio: one item is checked. |
| `Checks` | `list` | `[]` | check mode: the values that are checked. Two-way: give it a bare reference and the view writes it back. |
| `Selected` | `any` |  | radio mode: the value that is checked. Two-way: give it a bare reference and the view writes it back. |
| `Placement` | `below` or `above` or `start` or `end` | `below` | Which side of the anchor; it flips or shifts to fit. |
| `Width` | `float` | `200` | How wide the menu is, from 112 to 280 pixels. |
| `Focus_First` | `bool` | `false` | When it opens, the focus moves to its first row (a menu opened with the keyboard). |
| `On_Pick` | `handler` |  | Called after an item has been chosen (a submenu uses it to close the menu it came from). |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `surface` (Container), `row` (Container), `divider` (Divider), `heading` (Text), `item` (MenuItem), `parent_item` (MenuItem), `sub` (Menu).

Its look is in [`Menu_Stylesheet.tdl`](../stylesheets/menus/menu.md).

### `MenuItem`

One row of a menu (Material 3): 48 pixels tall, `label_large` text, an optional 24 pixel leading icon, trailing text such as a keyboard shortcut, and a chevron when it opens a submenu. `Checked` makes it a checkable item: true shows a check where the icon would be, false leaves the space, and nothing (null) is no check at all. It is pressable (a state layer, a ripple, Enter); `Handlers: {On_Click: ...}` on the call is what a press does. Roles: a `menuitem`, with `Checked` for a checkable one.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Label` | `str` |  | The text. |
| `Icon` | `str` |  | A leading icon. |
| `Trailing_Text` | `str` |  | Text at the end, such as a shortcut. |
| `Hint` | `str` |  | A line of explanation under the label (`body_small`, `on_surface_variant`, up to two lines): the row grows to hold it. |
| `Checked` | `any` |  | true: a check shows; false: its space is kept; empty: not checkable. |
| `Submenu` | `bool` | `false` | A chevron at the end: the item opens another menu. |
| `Disabled` | `bool` | `false` | Dimmed, not focusable, and it does not respond. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `lead` (Icon), `lead_space` (Container), `label` (Text), `filler` (Container), `trailing` (Text), `chevron` (Icon).

Its look is in [`MenuItem_Stylesheet.tdl`](../stylesheets/menus/menu-item.md).

## Using it

```tdl
Container {
  Name: editor
  Style { Width: 480, Height: 360 }
  Children {
    Button {
      Name: more
      Label: More
      Handlers {
        On_Click { Set { Target: open, Value: <| True |> } }
      }
    }
    Menu {
      Open: <| open |>
      Anchor: more
      Chosen: <| command |>
      Items {
        Item { Value: cut, Label: Cut, Shortcut: "Ctrl+X" }
        Item { Value: copy, Label: Copy, Icon: content_copy }
        Item { Divider: true }
        Item { Value: share, Label: Share, Submenu { Item { Value: mail, Label: Mail }, Item { Value: link, Label: Link } } }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import menu

actions = menu(app.window, [("Cut", viewmodel.cut), ("Copy", viewmodel.copy)], width=200)
actions.open(save.node)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Menu_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Menu
    Part: surface
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Overlays](../guide/overlays.md)
- [Effects](../guide/effects.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
