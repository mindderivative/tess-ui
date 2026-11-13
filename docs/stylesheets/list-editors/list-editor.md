# ListEditor_Stylesheet.yaml

The look of ListEditor: the empty note in `on_surface_variant` and a message in `error`; the rows, the text fields, the spin boxes, the switches, the menus and the colour pickers in them look as their own widgets do.

The look of [`ListEditor`](../../components/list-editors.md) (in [List editor](../../components/list-editors.md)). [How component stylesheets work](../index.md).

## The stylesheet

```yaml
tesserae: 0.6
# The look of ListEditor: the empty note in `on_surface_variant` and a message in `error`; the rows, the text fields, the spin boxes, the switches, the menus and the colour pickers in them look as their own widgets do.
styles:
  - {widget: ListEditor, part: empty, style: {foreground: on_surface_variant}}
  - {widget: ListEditor, part: message_text, style: {foreground: error}}
```

## How it reaches the view

Each rule names `widget: ListEditor` and may add the properties the view declares (a `variant`, a `size`, a `shape`), `classes`, a node `name`, a `part` (one of the view's named nodes) and a `state` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `name`, then the number of properties matched (all the `classes` count as one more), then a `state`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `style:` beats every rule for the fields it sets.

## The rules

### `empty` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `message_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `error` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```yaml
styles:
  - widget: ListEditor
    part: empty
    style: {foreground: tertiary}
```
