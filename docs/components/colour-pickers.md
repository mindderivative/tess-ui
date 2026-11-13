# Colour picker

*Selection and input*

## In Material Design 3

Material Design 3 has no colour picker of its own: it chooses colours for an app's theme, not for the content in it. A colour picker is how a person chooses a colour for
something they make, here from a square of saturation and value, a strip of hues and a strip of alpha, as colour editors do, and from the colours of the theme.

## In Tesserae

Two views and four controls. `ColourPicker` is the view you use: the picker inline, or (`popup: true`) a 40 pixel swatch of the colour that opens it in a layer next to it.
`ColourPickerPanel` is the inside of it, with no surface and no trigger, for an app that lays the parts out itself. `ColourArea`, `ColourStrip`, `ColourField` and
`ColourSwatches` are Tesserae controls (`tess_ui.colour_controls`): the parts of the panel, each of which can be used alone.

`value` is the colour as text, and is two-way: `'#rrggbb'`, or `'#rrggbbaa'` when the alpha is below 1 (lowercase; a fully opaque colour never has the alpha digits). Capitals
are read and written back in lowercase, and anything else (`#fff`, `red`) is an error that names the widget. Every part reads and writes the one text, so they stay in step, and
setting a value and reading it back gives the same text. The square and the strips are drawn with the engine's gradients.

The square (`ColourArea`) is saturation across and value up, for the hue; a press or a drag sets both and keeps the hue and the alpha. The hue strip (`ColourStrip` with
`channel: hue`) runs through the rainbow from 0 to 360 degrees and the alpha strip (`channel: alpha`) from clear to the colour over a chequerboard, from 0 to 100 percent.
A grey and a black have no hue of their own, so the picker remembers the hue (`hue`, a number of degrees the square and the hue strip share) and keeps it while the text still
agrees with it: a drag to a corner and back, or through white or black, ends at the hue it began with, and a drag of the hue strip leaves the saturation and value as they were.

The hex field (`ColourField` with `channel: hex`) takes `#rrggbb` or `#rrggbbaa`, and the red, green, blue and alpha fields a whole number from 0 to 255. What is typed sets the value
at once while it is a colour; while it is not, the value stays as it was and the field is drawn in the error colours and tells a screen reader it is invalid. Leaving the field, or
Escape, puts back the text of the value. The up and down arrows step a number by one, by ten with Shift. The swatches (`ColourSwatches`) are the theme's colour roles, by default
`primary`, `secondary`, `tertiary`, `error`, `surface`, `on_surface`, `primary_container` and `secondary_container` (`roles` names others); pressing one sets the value to that
role's colour, opaque, and the swatch whose colour is the value's is drawn selected.

With `popup: true`, `open` is two-way: pressing the swatch opens the picker, and Escape or a press outside closes it and writes false to `open` (pressing the swatch again closes it too).
A disabled picker does not open. `on_change` is called after each change the user makes, while a drag is still going; changes the app makes by setting the value do not call it.

The keyboard: Tab goes square, hue, alpha, the hex field, red, green, blue, alpha, then each swatch. The arrow keys move the point of the square by a hundredth of saturation or
value, by a tenth with Shift; Page Up and Page Down move the value by a tenth; Home and End take the saturation to its ends. On a strip the arrows move a degree or a percent (ten
with Shift), Page Up and Page Down ten, and Home and End go to the ends. Left and Right move between swatches. For a screen reader the square is a slider that says "saturation 40 percent,
value 80 percent", the hue strip one in degrees and the alpha strip one in percent, each can be incremented, decremented and set, and the whole picker is a group named by `label`.

The look is in `ColourPicker_Stylesheet.yaml`: write one in your project to change the swatch and the layer. The swatch has the state layer, ripple and focus ring of a pressable node and
a disabled picker fades to 38%. Not built: a picker that follows a drag to the alpha digits of a colour written with `rgb()`, other colour spaces (HSL, OKLCH), an eyedropper,
a recent-colours row, and a swatch row that shows the theme's colours of the other mode.

## How it is built

A view Tesserae ships is a `<Name>_View.yaml` (what it takes and what it is made of) with a `<Name>_Stylesheet.yaml` (how it looks). Use it by name: `widget: ColourPicker`. A file of the same name in your project replaces it.

### `ColourPicker`

The colour picker: a square of saturation and value, hue and alpha strips, a hex field, red, green, blue and alpha numbers, and a row of the theme's colour roles, either inline or (`popup: true`) behind a swatch of the colour that opens it in a layer next to it. `value` is two-way: '#rrggbb' text, or '#rrggbbaa' when the alpha is below 1 (lowercase). Escape and a press outside close the popup (writing false to `open`). `on_change` is called after each change the user makes, while a drag is still going. What the parts do is in ColourPickerPanel.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | `str` | `#000000` | The colour: '#rrggbb', or '#rrggbbaa' when its alpha is below 1 (lowercase). Two-way: give it a bare reference and the view writes it back. |
| `popup` | `bool` | `false` | Show a swatch of the colour that opens the picker in a layer, instead of the picker itself. |
| `open` | `bool` | `false` | A popup picker: whether it is showing; Escape and a press outside write false. Two-way: give it a bare reference and the view writes it back. |
| `roles` | `list` | `[]` | The theme colour roles in the row of swatches, in order; empty for primary, secondary, tertiary, error, surface, on_surface, primary_container and secondary_container. |
| `label` | `str` | `Colour` | What a screen reader calls the picker, and the swatch that opens it. |
| `disabled` | `bool` | `false` | Dimmed and not editable; a popup does not open. |
| `on_change` | `handler` |  | Called after each change the user makes. |

Its parts, by name (a stylesheet rule's `part:` or `name:` addresses one): `trigger` (Container), `layer` (Overlay), `surface` (Container), `popup_panel` (ColourPickerPanel), `panel` (ColourPickerPanel).

Its look is in [`ColourPicker_Stylesheet.yaml`](../stylesheets/colour-pickers/colour-picker.md).

### `ColourPickerPanel`

The inside of a colour picker, with no surface and no trigger: a square of saturation and value for the hue, a hue strip, an alpha strip, the hex text, the red, green, blue and alpha numbers, and a row of the theme's colour roles. `value` is two-way and holds the colour as '#rrggbb' text, or '#rrggbbaa' when its alpha is below 1 (lowercase). Every part reads and writes `value`, so they stay in step, and the hue the picker remembers (kept in `hue`, for a grey or a black, which have none of their own) is shared by the square and the hue strip. `on_change` is called after each change the user makes, while a drag is still going. Tab goes square, hue, alpha, hex, red, green, blue, alpha, swatches.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | `str` | `#000000` | The colour: '#rrggbb', or '#rrggbbaa' when its alpha is below 1 (lowercase). Two-way: give it a bare reference and the view writes it back. |
| `roles` | `list` | `[]` | The theme colour roles in the row of swatches, in order; empty for primary, secondary, tertiary, error, surface, on_surface, primary_container and secondary_container. |
| `label` | `str` | `Colour` | What a screen reader calls the picker. |
| `disabled` | `bool` | `false` | Dimmed and not editable. |
| `on_change` | `handler` |  | Called after each change the user makes. |

Its parts, by name (a stylesheet rule's `part:` or `name:` addresses one): `square` (ColourArea), `hue_strip` (ColourStrip), `alpha_strip` (ColourStrip), `hex` (ColourField), `channels` (Container), `red` (ColourField), `green` (ColourField), `blue` (ColourField), `alpha` (ColourField), `swatches` (ColourSwatches).

### `ColourArea`

A square of saturation (across) and value (up) for the colour's hue, with a handle: drag it, or move it with the arrow keys (Shift for a bigger step).

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `value` | `str` | `#000000` | The colour: '#rrggbb', or '#rrggbbaa' when its alpha is below 1 (lowercase; capitals are read and written back lowercase). Two-way. |
| `hue` | `float` |  | The hue in degrees the picker remembers for a colour with none of its own (a grey, a black), so a drag to a corner and back keeps the hue; bind a `state:` name shared by the area and the hue strip. Two-way. |
| `label` | `str` | `Saturation and value` | What a screen reader calls it. |
| `disabled` | `bool` |  |  |

### `ColourStrip`

A strip with a handle that picks a colour's hue or its alpha: drag it, or use the arrow, Page Up, Page Down, Home and End keys.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `channel` | `hue` or `alpha` | `hue` | `hue` is the rainbow, 0 to 360 degrees; `alpha` is clear to the colour over a chequerboard, 0 to 100 percent. |
| `value` | `str` | `#000000` | The colour: '#rrggbb', or '#rrggbbaa' when its alpha is below 1 (lowercase; capitals are read and written back lowercase). Two-way. |
| `hue` | `float` |  | The hue in degrees the picker remembers for a colour with none of its own (a grey, a black), so a drag to a corner and back keeps the hue; bind a `state:` name shared by the area and the hue strip. Two-way. |
| `label` | `str` |  | What a screen reader calls it. |
| `disabled` | `bool` |  |  |

### `ColourField`

A text field for the colour. A valid entry sets `value` at once; an invalid one leaves it and shows the field in the error colours.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `channel` | `hex` or `red` or `green` or `blue` or `alpha` | `hex` | `hex` takes '#rrggbb' or '#rrggbbaa'; the others take a whole number from 0 to 255. |
| `value` | `str` | `#000000` | The colour: '#rrggbb', or '#rrggbbaa' when its alpha is below 1 (lowercase; capitals are read and written back lowercase). Two-way. |
| `label` | `str` |  | What a screen reader calls it. |
| `disabled` | `bool` |  |  |

### `ColourSwatches`

A row of the theme's colour roles; pressing one sets `value` to its colour.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `roles` | `list` |  | The theme colour roles to show, in order (primary, secondary, tertiary, error, surface, on_surface, primary_container and secondary_container when left out). |
| `value` | `str` | `#000000` | The colour: '#rrggbb', or '#rrggbbaa' when its alpha is below 1 (lowercase; capitals are read and written back lowercase). Two-way. |
| `label` | `str` | `Theme colours` | What a screen reader calls the row. |
| `disabled` | `bool` |  |  |

## Using it

```yaml
name: paint
widget: Container
style: {flex_direction: horizontal, gap: 24, width: 640, height: 560, padding: 16}
children:
  - {widget: ColourPicker, value: "{{ fill }}", on_change: recolour}
  - widget: Container
    style: {flex_direction: vertical, gap: 8}
    children:
      - {widget: ColourPicker, popup: true, open: "{{ choosing }}", value: "{{ fill }}", label: Fill colour}
      - {widget: ColourPicker, popup: true, open: "{{ choosing_line }}", value: "{{ line }}", label: Line colour, roles: [primary, error, on_surface]}
```

## Using it in Python

```python
from tess_ui.widgets import colour_area, colour_field, colour_strip

area = colour_area(app.window, "#3366cc", x=16, y=16)
hue = colour_strip(app.window, "hue", "#3366cc", x=16, y=204)
hex_field = colour_field(app.window, "hex", "#3366cc", x=16, y=240)
area.on_input(lambda text: hex_field.value.set(text))
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.yaml` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `style:` beats every rule:

```yaml
# ColourPicker_Stylesheet.yaml, or any stylesheet your app loads
styles:
  - widget: ColourPicker
    part: surface
    style: {background: tertiary}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Controls](../guide/controls.md)
- [Widget Catalog](../guide/widget-catalog.md)
- [Python API reference](../api/python.md)
- [YAML reference](../api/yaml.md)
