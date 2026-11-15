# ListEditor_Stylesheet.tdl

The look of ListEditor: the empty note in `on_surface_variant` and a message in `Error`; the rows, the text fields, the spin boxes, the switches, the menus and the colour pickers in them look as their own widgets do.

The look of [`ListEditor`](../../components/list-editors.md) (in [List editor](../../components/list-editors.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: ListEditor
Tesserae: "0.6"
---
# The look of ListEditor: the empty note in `on_surface_variant` and a message in `error`; the rows, the text fields, the spin boxes, the switches, the menus and the colour pickers in them look as their own widgets do.
Styles {
  Rule { Widget: ListEditor, Part: empty, Style { Foreground: on_surface_variant } }
  Rule { Widget: ListEditor, Part: message_text, Style { Foreground: error } }
}
```

## How it reaches the view

Each rule names `Widget: ListEditor` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `empty` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `message_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `error` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: ListEditor
    Part: empty
    Style { Foreground: tertiary }
  }
}
```
