# FileDialog_Stylesheet.yaml

The look of FileDialog: a `surface_container_high` panel with 28 pixel corners, 24 pixels of padding and 12 between its parts at level 3, as Dialog has; the title in `on_surface`; the column headings and the list's size and time columns in `on_surface_variant`; a row 40 pixels tall with 12 pixel corners; a message in `error`, or in `on_surface_variant` for the empty folder.

The look of [`FileDialog`](../../components/file-dialogs.md) (in [File dialog](../../components/file-dialogs.md)). [How component stylesheets work](../index.md).

## The stylesheet

```yaml
tesserae: 0.6
# The look of FileDialog: a `surface_container_high` panel with 28 pixel corners, 24 pixels of padding and 12 between its parts at level 3, as Dialog has; the title in `on_surface`; the column
# headings and the list's size and time columns in `on_surface_variant`; a row 40 pixels tall with 12 pixel corners; a message in `error`, or in `on_surface_variant` for the empty folder.
styles:
  - widget: FileDialog
    part: panel
    style: {background: surface_container_high, corner_radius: 28, padding: 24, gap: 12, elevation: 3}
  - {widget: FileDialog, part: headline, style: {foreground: on_surface}}
  - {widget: FileDialog, part: browser, style: {position: absolute, width: 0, height: 0}}
  - {widget: FileDialog, part: columns, style: {padding: {left: 8, right: 8, top: 0, bottom: 0}}}
  - {widget: FileDialog, part: column_name, style: {foreground: on_surface_variant}}
  - {widget: FileDialog, part: column_size, style: {foreground: on_surface_variant}}
  - {widget: FileDialog, part: column_modified, style: {foreground: on_surface_variant}}
  - {widget: FileDialog, part: row, style: {corner_radius: 12}}
  - {widget: FileDialog, part: row_icon, style: {foreground: on_surface_variant, width: 24, height: 24}}
  - {widget: FileDialog, part: row_name, style: {foreground: on_surface}}
  - {widget: FileDialog, part: row_size, style: {foreground: on_surface_variant}}
  - {widget: FileDialog, part: row_modified, style: {foreground: on_surface_variant}}
  - {widget: FileDialog, part: empty, style: {foreground: on_surface_variant}}
  - {widget: FileDialog, part: message_text, style: {foreground: error}}
  - {widget: FileDialog, part: crumb_gap, style: {foreground: on_surface_variant, width: 20, height: 20}}
  - widget: FileDialog
    part: replace_panel
    style: {background: surface_container_high, corner_radius: 28, padding: 24, gap: 16, elevation: 3}
  - {widget: FileDialog, part: replace_headline, style: {foreground: on_surface}}
  - {widget: FileDialog, part: replace_body, style: {foreground: on_surface_variant}}
```

## How it reaches the view

Each rule names `widget: FileDialog` and may add the properties the view declares (a `variant`, a `size`, a `shape`), `classes`, a node `name`, a `part` (one of the view's named nodes) and a `state` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `name`, then the number of properties matched (all the `classes` count as one more), then a `state`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `style:` beats every rule for the fields it sets.

## The rules

### `panel` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `background` | `surface_container_high` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `corner_radius` | `28` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`top`, `right`, `bottom`, `left`) with the rest square. |
| always | `padding` | `24` | Space inside it: one number, or `{left, right, top, bottom}`. |
| always | `gap` | `12` | Space between its children. |
| always | `elevation` | `3` | A shadow level, 0 to 5. |

### `headline` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `browser` (FileBrowser)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `position` | `absolute` | `absolute` takes it out of the flow and places it at `x` and `y`. |
| always | `width` | `0` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `height` | `0` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `columns` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `padding` | `{bottom: 0, left: 8, right: 8, top: 0}` | Space inside it: one number, or `{left, right, top, bottom}`. |

### `column_name` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `column_size` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `column_modified` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `row` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `corner_radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`top`, `right`, `bottom`, `left`) with the rest square. |

### `row_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `row_name` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `row_size` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `row_modified` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `empty` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `message_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `error` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `crumb_gap` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `width` | `20` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `height` | `20` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `replace_panel` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `background` | `surface_container_high` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `corner_radius` | `28` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`top`, `right`, `bottom`, `left`) with the rest square. |
| always | `padding` | `24` | Space inside it: one number, or `{left, right, top, bottom}`. |
| always | `gap` | `16` | Space between its children. |
| always | `elevation` | `3` | A shadow level, 0 to 5. |

### `replace_headline` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `replace_body` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```yaml
styles:
  - widget: FileDialog
    part: panel
    style: {background: tertiary}
```
