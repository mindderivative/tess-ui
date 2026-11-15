# FileDialog_Stylesheet.tdl

The look of FileDialog: a `surface_container_high` panel with 28 pixel corners, 24 pixels of padding and 12 between its parts at level 3, as Dialog has; the title in `on_surface`; the column headings and the list's size and time columns in `on_surface_variant`; a row 40 pixels tall with 12 pixel corners; a message in `Error`, or in `on_surface_variant` for the empty folder.

The look of [`FileDialog`](../../components/file-dialogs.md) (in [File dialog](../../components/file-dialogs.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: FileDialog
Tesserae: "0.6"
---
# The look of FileDialog: a `surface_container_high` panel with 28 pixel corners, 24 pixels of padding and 12 between its parts at level 3, as Dialog has; the title in `on_surface`; the column
# headings and the list's size and time columns in `on_surface_variant`; a row 40 pixels tall with 12 pixel corners; a message in `error`, or in `on_surface_variant` for the empty folder.
Styles {
  Rule {
    Widget: FileDialog
    Part: panel
    Style { Background: surface_container_high, Corner_Radius: 28, Padding: 24, Gap: 12, Elevation: 3 }
  }
  Rule { Widget: FileDialog, Part: headline, Style { Foreground: on_surface } }
  Rule { Widget: FileDialog, Part: browser, Style { Position: absolute, Width: 0, Height: 0 } }
  Rule { Widget: FileDialog, Part: columns, Style { Padding { Left: 8, Right: 8, Top: 0, Bottom: 0 } } }
  Rule { Widget: FileDialog, Part: column_name, Style { Foreground: on_surface_variant } }
  Rule { Widget: FileDialog, Part: column_size, Style { Foreground: on_surface_variant } }
  Rule { Widget: FileDialog, Part: column_modified, Style { Foreground: on_surface_variant } }
  Rule { Widget: FileDialog, Part: row, Style { Corner_Radius: 12 } }
  Rule { Widget: FileDialog, Part: row_icon, Style { Foreground: on_surface_variant, Width: 24, Height: 24 } }
  Rule { Widget: FileDialog, Part: row_name, Style { Foreground: on_surface } }
  Rule { Widget: FileDialog, Part: row_size, Style { Foreground: on_surface_variant } }
  Rule { Widget: FileDialog, Part: row_modified, Style { Foreground: on_surface_variant } }
  Rule { Widget: FileDialog, Part: empty, Style { Foreground: on_surface_variant } }
  Rule { Widget: FileDialog, Part: message_text, Style { Foreground: error } }
  Rule { Widget: FileDialog, Part: crumb_gap, Style { Foreground: on_surface_variant, Width: 20, Height: 20 } }
  Rule {
    Widget: FileDialog
    Part: replace_panel
    Style { Background: surface_container_high, Corner_Radius: 28, Padding: 24, Gap: 16, Elevation: 3 }
  }
  Rule { Widget: FileDialog, Part: replace_headline, Style { Foreground: on_surface } }
  Rule { Widget: FileDialog, Part: replace_body, Style { Foreground: on_surface_variant } }
}
```

## How it reaches the view

Each rule names `Widget: FileDialog` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `panel` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `surface_container_high` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Corner_Radius` | `28` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Padding` | `24` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `12` | Space between its children. |
| always | `Elevation` | `3` | A shadow level, 0 to 5. |

### `headline` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `browser` (FileBrowser)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Position` | `absolute` | `absolute` takes it out of the flow and places it at `X` and `Y`. |
| always | `Width` | `0` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `0` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `columns` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `{ Left: 8, Right: 8, Top: 0, Bottom: 0 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

### `column_name` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `column_size` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `column_modified` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `row` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Corner_Radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |

### `row_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `row_name` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `row_size` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `row_modified` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `empty` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `message_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `error` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `crumb_gap` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Width` | `20` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `20` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `replace_panel` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `surface_container_high` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Corner_Radius` | `28` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Padding` | `24` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `16` | Space between its children. |
| always | `Elevation` | `3` | A shadow level, 0 to 5. |

### `replace_headline` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `replace_body` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: FileDialog
    Part: panel
    Style { Background: tertiary }
  }
}
```
