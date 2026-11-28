# Menu bars

*Navigation*

## In Material Design 3

Material 3 has no menu bar (it targets touch and has the top app bar); this is the desktop one of the Tesserae UX specification: a row of titles across the top of a window, each opening a menu of
commands with their shortcuts beside them.

## In Tesserae

`MenuBar` is a view Tesserae ships (`MenuBar_View.tdl`): a row of titles, each with a `Menu` opened under it. `Menus` is a list of `{label, items}` (and `disabled`); the `items` are the rows a `Menu` takes, and
the `value` of the row pressed goes to `Chosen`. A `&` in a label marks the mnemonic letter (`&File`), underlined while the bar is active (`Mnemonics: on_alt`, the default; `always`, `never`).

The bar is one Tab stop; Left and Right (Home, End, a letter) move between titles and skip a disabled one, and Down, Up, Enter and Space open the menu with its first row in focus. With a menu open,
Left and Right on a row that has no submenu open the previous and the next title's menu, and the pointer over another title opens that one at once; pressing an open title closes it. Alt pressed and released
alone, or F10, focus the first title and make the bar active (the same again, or Escape, gives the focus back); Alt and the mnemonic letter open that menu from anywhere in the window. The bar
and its titles are as high as a control of the density (40, 32, 28), and its menus take the same density. A shortcut shown in a row is the caller's to bind; the menu only shows it.

Not built yet: the overflow ("More") item for titles that do not fit, and Up opening the menu at its last row (it opens at the first). The role is `group` named `Label` until the engine has `menubar`.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `MenuBar { ... }`. A file of the same name in your project replaces it.

### `MenuBar`

The desktop menu bar: a row of titles (File, Edit, View ...) across the top of a window, each opening a `Menu` of commands (ux spec Menu Bar; Material 3 has none). `Menus` is a list of {label, items} and optionally {disabled}: `Label` may mark a mnemonic letter with `&` (`&File`: the F is underlined while the bar is active, and Alt+F opens the menu from anywhere in the window), `Items` are the rows of a Menu ({value, label} and optionally {icon, shortcut, checked, disabled, submenu}, {divider: true}); pressing a row sets `Chosen` to its `Value`. The bar is one Tab stop; Left and Right (and Home, End, a letter) move between the titles, Down, Up, Enter and Space open the menu with its first row in focus; with a menu open Left and Right on a row without a submenu open the previous and the next title's menu, and the pointer moving over another title opens that one at once. Alt pressed and released alone, or F10, makes the bar active (focus on its first title, mnemonics shown); Escape leaves it. A shortcut shown in a row is the caller's to bind: the menu only shows it. The role is `Group` named `Label` until the engine has `menubar`.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Menus` | `list` | `[]` | The titles, each {label, items} and optionally {disabled}; `&` before a letter of `Label` marks its mnemonic. |
| `Chosen` | `any` |  | The value of the row last pressed in any menu. Two-way: give it a bare reference and the view writes it back. |
| `Label` | `str` | `"Menu bar"` | The bar's accessible name. |
| `Mnemonics` | `on_alt` or `always` or `never` | `on_alt` | on_alt: the underlines show while the bar is active; always: at rest too; never: not at all (the Alt+letter keys still work). |
| `Menu_Width` | `float` | `240` | How wide each menu is, from 112 to 280 pixels. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `strip` (Container), `title` (Container), `label` (Text), `menu` (Menu).

Its look is in [`MenuBar_Stylesheet.tdl`](../stylesheets/menu-bars/menu-bar.md).

## Using it

```tdl
Container {
  Name: window
  Style { Width: 480, Height: 240 }
  Children {
    MenuBar {
      Chosen: <| command |>
      Menus {
        Item { Label: "&File", Items { Item { Value: new, Label: New, Shortcut: "Ctrl+N" }, Item { Value: save, Label: Save, Shortcut: "Ctrl+S" } } }
        Item { Label: "&Edit", Items { Item { Value: undo, Label: Undo, Shortcut: "Ctrl+Z" } } }
      }
    }
  }
}
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# MenuBar_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: MenuBar
    Part: label
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Overlays](../guide/overlays.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
