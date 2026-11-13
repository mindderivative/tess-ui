# Icon picker

*Selection and input*

## In Material Design 3

Material Design 3 has no icon picker: icons are chosen by the people who design an app. An app whose people pick an icon for something (a launcher, a button, a block of a configuration)
needs one, and it is built from what MD3 does describe: an outlined text field for the search, a grid of selectable items, and a menu-like surface that holds them.

## In Tesserae

Two views and one control. `IconPicker` is the view you use: the picker inline, or (`popup: true`) a 48 pixel button that shows the icon and its name and opens the picker in a layer under it.
`IconPickerPanel` is the inside of it, with no surface and no button. `IconBrowser` is the control that draws nothing and is the picker's mind (`tess_ui.icon_controls`): the list, the search,
the cursor and the previews, which the view reaches through the names it binds to it.

The icons are the curated set of `tess_ui.icons` (Material Symbols and Material Design Icons, by name) and, when `icons_folder` is given, the `.svg` and `.png` files in that folder, which come
first. `value` is two-way text: a built-in icon's name (`home`), or a file's name with its extension (`logo.svg`). A value that is not an icon the picker knows is kept as it is and nothing is
selected. The folder is read through `tess_ui.filesystem`, once when the grid opens (a popup reads nothing until it does); a folder that cannot be read is a message under the grid, and the built-in
icons stay. A file is shown as its picture: an SVG is drawn in the text colour where it says `currentColor`, a PNG is scaled down to fit. A file is read only when its row comes into view, a file
that is not an SVG or a picture is shown as a plain file glyph, and a document type or entity declaration in an SVG is refused.

The search field keeps the icons whose name has every word of what is typed, in any order, without regard to case, with `_`, `-` and `.` counted as spaces (`arrow back` finds `arrow_back`, `svg`
finds `logo.svg`); a name that starts with the first word comes first. The grid is a `VirtualList` of rows of `columns` icons (8 by default), `rows` of them in view (6): it builds the rows in view and
three past each edge, however many icons there are, and a new search makes new rows rather than patching the old ones. It opens scrolled so that `value` shows, with the cursor on it.

The keyboard. The search field has the focus when a popup opens: Up, Down, Page Up and Page Down move the cursor in the grid and Enter picks the icon under it (Left, Right, Home, End and Space are the
text's). Tab goes on to the grid, where the arrow keys move by an icon and by a row, Home and End go to the start and end of the row (with Ctrl, of the whole grid), Page Up and Page Down go `rows` rows,
and Enter and Space pick. The grid scrolls to keep the cursor in view. A press picks too. A pick writes `value`, calls `on_change`, and closes a popup unless `close_on_pick` is false. Escape and a
press outside close a popup (writing false to `open`), and the focus goes back to the button. A screen reader hears a group named by `label`, a `list` of `listitem`s each named by its icon and
`selected` when it is the value, the search field, a button that says "label: icon" and is `expanded` while the layer is open, and an alert for a folder that cannot be read or a search that finds nothing.

The look is in `IconPicker_Stylesheet.yaml` and `IconPickerPanel_Stylesheet.yaml`: write one in your project to change the button, the layer and the cells. Not built: icon categories or
tags, recently used icons, other file types (`.jpg`, `.webp`), an icon's own colour for a PNG, sizes other than 24 pixels.

## How it is built

A view Tesserae ships is a `<Name>_View.yaml` (what it takes and what it is made of) with a `<Name>_Stylesheet.yaml` (how it looks). Use it by name: `widget: IconPicker`. A file of the same name in your project replaces it.

### `IconPicker`

The icon picker: a searchable grid of icons, either inline or (`popup: true`) behind a button that shows the icon and its name and opens the grid in a layer next to it. The icons are the curated set of `tess_ui.icons` and the `.svg` and `.png` files of `icons_folder` (read through `tess_ui.filesystem`, and only when the grid opens). `value` is two-way: the icon's name, or a file's name with its extension. Escape and a press outside close the popup (writing false to `open`); a pick closes it too, unless `close_on_pick` is false. `on_change` is called after each pick. What the grid does is in IconPickerPanel.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | `str` |  | The icon: a built-in icon's name, or a file's name with its extension. Two-way: give it a bare reference and the view writes it back. |
| `popup` | `bool` | `false` | Show a button with the icon that opens the grid in a layer, instead of the grid itself. |
| `open` | `bool` | `false` | A popup picker: whether it is showing; Escape, a pick and a press outside write false. Two-way: give it a bare reference and the view writes it back. |
| `close_on_pick` | `bool` | `true` | A popup picker closes when an icon is picked. |
| `icons_folder` | `str` |  | A folder of .svg and .png files offered besides the built-in icons. |
| `columns` | `int`, 3 to 16 | `8` | How many icons are in a row. |
| `rows` | `int`, 2 to 12 | `6` | How many rows show at once. |
| `label` | `str` | `Icon` | What a screen reader calls the picker, and the button that opens it. |
| `placeholder` | `str` | `Choose an icon` | What the button says while there is no icon. |
| `disabled` | `bool` | `false` | Dimmed and not editable; a popup does not open. |
| `on_change` | `handler` |  | Called after each pick. |

Its parts, by name (a stylesheet rule's `part:` or `name:` addresses one): `swatch` (IconBrowser), `field` (Container), `trigger_icon` (Icon), `trigger_svg` (Svg), `trigger_image` (Image), `trigger_text` (Text), `trigger_chevron` (Icon), `trigger` (Container), `layer` (Overlay), `surface` (Container), `popup_panel` (IconPickerPanel), `panel` (IconPickerPanel).

Its look is in [`IconPicker_Stylesheet.yaml`](../stylesheets/icon-pickers/icon-picker.md).

### `IconPickerPanel`

The inside of an icon picker, with no surface and no trigger: a search field over a grid of icons (the built-in set, and the `.svg` and `.png` files of `icons_folder`). `value` is two-way: the icon's name, or a file's name with its extension. A press picks an icon; in the grid the arrow keys, Home and End (with Ctrl, of the whole grid), Page Up and Page Down move the cursor and Enter or Space pick it; in the search field Up, Down, Page Up and Page Down move the cursor in the grid and Enter picks it. The grid is a `VirtualList` of rows of `columns` icons that builds the rows in view and a few past them, and a file is read (for its preview) only when its row comes into view. `on_change` is called after each pick. Nothing is listed until `open` is true (a popup's panel is open while the popup shows). What the parts do is in the IconBrowser control (`tess_ui.icon_controls`), which this view drives by writing a numbered command to `cmd`.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | `str` |  | The icon: a built-in icon's name, or a file's name with its extension. Two-way: give it a bare reference and the view writes it back. |
| `icons_folder` | `str` |  | A folder of .svg and .png files offered besides the built-in icons. |
| `columns` | `int`, 3 to 16 | `8` | How many icons are in a row. |
| `rows` | `int`, 2 to 12 | `6` | How many rows show at once. |
| `open` | `bool` | `true` | Whether the grid is listed and answers; a popup's panel is open while the popup shows. |
| `label` | `str` | `Icon` | What a screen reader calls the picker. |
| `disabled` | `bool` | `false` | Dimmed and not editable. |
| `on_change` | `handler` |  | Called after each pick. |

Its parts, by name (a stylesheet rule's `part:` or `name:` addresses one): `browser` (IconBrowser), `search` (TextField), `list_group` (Container), `list_box` (Container), `list` (VirtualList), `row` (Container), `cell` (Container), `cell_icon` (Icon), `cell_svg` (Svg), `cell_image` (Image), `empty` (Text), `message_text` (Text).

Its look is in [`IconPickerPanel_Stylesheet.yaml`](../stylesheets/icon-pickers/icon-picker-panel.md).

### `IconBrowser`

The icon picker's mind: it draws nothing. It lists the built-in icons and the files of a folder, searches them, keeps the cursor, reads the previews of the files in view and tells the view through the names it is bound to.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | `str` |  | The icon: a built-in icon's name, or the file name (with its extension) of one in `folder`. A pick writes it. Two-way. |
| `open` | `bool` | `true` | Whether the grid is listed: going true reads `folder`; nothing is read before. `current` is kept either way. |
| `folder` | `str` |  | A folder of `.svg` and `.png` files to offer besides the built-in icons; read through `tess_ui.filesystem`. |
| `query` | `str` |  | The search text: an icon is kept when its name has every word of it (`arrow back` finds `arrow_back`). |
| `columns` | `int` | `8` | How many icons are in a row (for the arrow keys and the rows of `grid`). |
| `rows` | `int` | `6` | How many rows show at once (for Page Up and Page Down and for scrolling the cursor into view). |
| `row_height` | `float` | `48.0` | How tall a row is, in pixels. |
| `command` | `str` |  | What to do, written as text that starts with a number that is new each time (`7 key arrow_down`): `key arrow_down ctrl`, `key arrow_up field` (from the search field), `click 12`, `refresh`. |
| `scroll` | `float` |  | The grid's scroll offset: bind the list's `scroll_offset` to the same name; moving the cursor writes the offset that shows it. Two-way. |
| `grid` | `list` |  | Output: written to the name it is bound to. The results in rows; each row {key, cells}, a cell {index, name, kind (glyph, svg, png or file), icon, svg, frame}. Two-way. |
| `cursor` | `int` |  | Output: written to the name it is bound to. The cell the keyboard is on, or -1. Two-way. |
| `count` | `int` |  | Output: written to the name it is bound to. How many icons the search found. Two-way. |
| `current` | `any` |  | Output: written to the name it is bound to. The cell of `value`, for the swatch that opens the picker (kind `none` when it is not an icon the picker knows). Two-way. |
| `message` | `str` |  | Output: written to the name it is bound to. What last went wrong, such as a folder that cannot be read; empty when nothing has. Two-way. |
| `disabled` | `bool` |  |  |

## Using it

```yaml
name: blocks
widget: Container
style: {flex_direction: vertical, gap: 16, width: 480, height: 640, padding: 16}
children:
  - {widget: IconPicker, popup: true, open: "{{ choosing }}", value: "{{ icon }}", icons_folder: ~/.config/myapp/Icons, label: Launcher icon, on_change: icon_changed}
  - {widget: IconPicker, value: "{{ icon }}", columns: 6, rows: 4}
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.yaml` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `style:` beats every rule:

```yaml
# IconPicker_Stylesheet.yaml, or any stylesheet your app loads
styles:
  - widget: IconPicker
    part: surface
    style: {background: tertiary}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Controls](../guide/controls.md)
- [Colour Pickers](../components/colour-pickers.md)
- [Python API reference](../api/python.md)
- [YAML reference](../api/yaml.md)
