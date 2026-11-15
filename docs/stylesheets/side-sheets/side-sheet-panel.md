# SideSheetPanel_Stylesheet.tdl

The look of the inside of a side sheet: 24 pixels beside the header and the content, 16 above the actions, the title in on_surface.

The look of [`SideSheetPanel`](../../components/side-sheets.md) (in [Side sheets](../../components/side-sheets.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: SideSheetPanel
Tesserae: "0.6"
---
# The look of the inside of a side sheet: 24 pixels beside the header and the content, 16 above the actions, the title in on_surface.
Styles {
  Rule {
    Widget: SideSheetPanel
    Style {
      Padding { Left: 24, Right: 16, Top: 0, Bottom: 24 }
    }
  }
  Rule { Widget: SideSheetPanel, Part: title, Style { Foreground: on_surface } }
  Rule { Widget: SideSheetPanel, Part: actions, Style { Padding { Left: 0, Right: 8, Top: 16, Bottom: 0 } } }
}
```

## How it reaches the view

Each rule names `Widget: SideSheetPanel` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `SideSheetPanel` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `{ Left: 24, Right: 16, Top: 0, Bottom: 24 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

### `title` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `actions` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `{ Left: 0, Right: 8, Top: 16, Bottom: 0 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: SideSheetPanel
    Part: title
    Style { Foreground: tertiary }
  }
}
```
