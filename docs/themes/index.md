# Themes

A theme decides how an app looks as a whole: its colours, its type, and the shapes
and shadows of its components. A stylesheet holds the style rules you add. This page
says what a theme is made of, how Tesserae applies one with a stylesheet, how to change each
part, and ends with the complete API.

## What a theme is

| Thing | Scope | Lives in | Set with |
| --- | --- | --- | --- |
| **Theme** | the whole app | `*_Theme.tdl` | `App(custom_theme=)` |
| **Stylesheet** | every view of the app | `*_Stylesheet.tdl` | `App(stylesheet=)` |
| **Shipped rules** | one view Tesserae ships | `<Name>_Stylesheet.tdl` in the package | a rule of your own goes over them: [Component Stylesheets](../stylesheets/index.md) |
| **Style** | one node | `Style` | the node |

A theme file holds the palette, the type and the shapes. Every key is optional:

```tdl
# Brand_Theme.tdl
Theme {
  Seed: "#0B6B58"              # the colour the whole palette is made from
  Dark: false                  # whether the theme is the dark scheme (the app decides: see below)
  Colors {                     # roles to replace, after the palette is made
    Tertiary: "#C2410C"
  }
  Typography {                 # changes to MD3's type styles
    Body_Large { Font_Family: Inter, Font_Size: 17 }
  }
  Components {                 # the shape and elevation of widgets made in Python
    Card {
      Elevated { Corner_Radius: 8, Elevation: level_2 }
    }
  }
}
```

A theme is a root `Theme` block, and a colour is a quoted string (`"#0B6B58"`; a bare `#` starts a comment). A stylesheet is a root `Styles` block holding `Rule` blocks (a key a stylesheet does not have, such as a `Seed`, is an error). The keys are listed in the [TDL reference](../api/tdl.md#the-theme).
A component with a dot in its name (`card.elevated`) is a block inside its component: `Card { Elevated { ... } }`.
Rules are written in a stylesheet, not a theme: a theme's own `Styles` list is read in the older rule shape (`Kind`,
`Classes`, `Id`) and is not how a view is styled now.

## How a node gets its style

A node's style is built from layers, lowest first. A later layer changes only the fields it mentions:

1. the **shipped rules** of the view or widget (Tesserae's own look for a `Button`, a `Card`, and so on);
2. the app's **stylesheet**;
3. the node's own **`Style`**.

A stylesheet is a list of rules. A rule names a `Widget` (a built-in or a view, yours or Tesserae's) and may narrow it:

```tdl
# Notes_Stylesheet.tdl
Styles {
  Rule { Widget: Container, Style { Padding: 12 } }                                   # every Container
  Rule { Widget: Container, Classes: [panel], Style { Background: surface_container_high } }   # a Container with the class `panel`
  Rule { Widget: Text, Name: title, Style { Foreground: primary } }                   # the node named `title`
  Rule { Widget: Button, Variant: filled, Style { Background: tertiary } }            # a property the widget declares
  Rule { Widget: Button, Variant: filled, Part: label, Style { Foreground: on_tertiary } }   # a named node inside the widget
  Rule { Widget: Button, State: hovered, Style { Elevation: 2 } }                     # while the pointer is over it
}
```

A rule may narrow by `Variant`, `Size` and `Shape` (properties the widget declares), `Classes`, `Name`, a `Part` (a node of the
widget's own view, named in its stylesheet page) and a `State` (`hovered`, `focused`, `focus_visible`, `pressed`, `disabled`, `selected`, `checked`,
`expanded`, `error`, `read_only`, `visited`). The most specific rule wins: a `Name`, then how many of `Variant`, `Size`, `Shape` and
`Classes` it names, then a `State`, then the widget alone; a later rule wins a tie. A node's own `Style` beats every rule, for the
fields it sets and no others, and a value in a rule may be an expression over the widget's properties (`<| height / 2 |>`).

A built-in view's look is its shipped rules, so restyling a part everywhere is a rule of your own with the same `Widget` and `Part`
in the app's stylesheet. See [Component Stylesheets](../stylesheets/index.md) for each widget's parts, and
[The View Language](../guide/view-language.md#style) for the rest.

## Colour

### From a seed

A theme's colours are made from one colour, the **seed**, by Material Design
3's algorithm: it builds a tonal palette and picks 49 named **roles** from it
(`primary`, `on_primary`, `surface`, `surface_container_high`, ...), once for
light and once for dark. The seed is the first of these that is set:

1. `App(theme_seed=(r, g, b, a))`;
2. the custom theme's `Seed`;
3. the default theme's `Seed`.

Then `Colors` replaces roles: the default theme's, then the custom theme's.

```python
app = App(theme_seed=(0x0B, 0x6B, 0x58, 0xFF), custom_theme="themes/Brand_Theme.tdl")
```

Anywhere a view takes a colour, the role's name works: `Background: surface`.

### With no theme

An app with no seed at all still resolves roles, from MD3's baseline palette
(the purple one). A `theme_seed=` is what makes the colours your own and lets
them follow the OS's light and dark. A role that doesn't exist, or is
misspelt, is an error that says so: `unknown color identifier -- did you mean
'surface'?`

### Colour values

Anywhere a view, stylesheet or theme takes a colour, it takes a string:

- hex: `#RGB`, `#RGBA`, `#RRGGBB` or `#RRGGBBAA`;
- a CSS colour name, or `transparent`;
- `rgb()`, `rgba()`, `hsl()` and `hsla()`, with commas or spaces and an optional alpha;
- CSS Color 4's `oklch()`, `oklab()`, `lch()`, `lab()`, `hwb()`, and `color()` in `srgb`,
  `srgb-linear`, `display-p3`, `a98-rgb`, `prophoto-rgb`, `rec2020`, `xyz`, `xyz-d50` or `xyz-d65`.

```text
Style {
  Background: "oklch(62.8% 0.2577 29.23)"   # sRGB red
  Foreground: "color(display-p3 0.2 0.3 0.1)"
}
```

Any of these, and any theme role, may end in `@N%` to scale its alpha: `primary@12%` is the primary colour at 12% (a state layer's
tint), `on_surface@38%` is disabled content, `"#6750A4@50%"` half of a hex colour, and a colour that already has alpha keeps that fraction
of it. The percentage is 0 to 100.

```text
Style {
  Background: "primary@12%"
  Border_Color: "on_surface@38%"
}
```

Tesserae renders in sRGB, so a colour outside it is clipped channel by channel. A colour's own
alpha renders (`"#FFFFFF80"` is half-transparent white), and `Opacity` fades a node and everything
in it as one layer; to dim a background without dimming what sits on it, put the transparency in the
colour. The built-in `Dialog` and `SideSheetModal` scrims do this, so a theme's `Colors { Scrim: ... }`
doesn't reach them.

## Light and dark

An `App` follows the OS by default (`dark="system"`): when the OS switches, every screen, widget,
control, overlay and the window's frame switch with it, in place. On Linux the starting appearance is known at
once, from the desktop's settings portal; on macOS and Windows it is known once the window opens, so
the app starts dark and switches on the first frame if the OS is light. Headless, it starts dark.

```python
app = App(theme_seed=(0x67, 0x50, 0xA4, 0xFF))   # follows the OS, from the start
app.set_dark(False)                               # light from now on
app.set_dark("system")                            # back to following the OS
```

Pass `dark=True` or `dark=False` to fix it. A widget made on the app's window with no `theme=` follows
the app; an explicit `theme=` pins it to that theme.

### Contrast and motion

The OS can also ask for more contrast and for less motion, and an app follows both by default.
`App(high_contrast="system")` takes MD3's highest-contrast colours when the OS asks for them, and
`App(reduced_motion="system")` makes animations take no time when it asks for that. Pass `True` or `False` to fix
either, or change them while the app runs:

```python
app = App(theme_seed=(0x67, 0x50, 0xA4, 0xFF), high_contrast=False, reduced_motion="system")
app.set_high_contrast(True)       # every screen re-themed in place
app.set_reduced_motion("system")  # back to following the OS
app.high_contrast, app.reduced_motion    # what is in force now
```

The look of a press and of keyboard focus is the app's too: `App(ripple="shader")` draws every ripple with one shader
instead of a circle node per press, and `App(focus_ring="gradient")` turns a gradient around the focus ring
instead of the solid one.

## Shape and elevation

A view's shape and elevation are style: `Corner_Radius` and `Elevation` in a rule or a node's `Style`, a number or one of MD3's
tokens. To change a widget's everywhere, write a rule for it in the app's stylesheet:

```tdl
Styles {
  Rule { Widget: Card, Variant: elevated, Style { Corner_Radius: 4, Elevation: 5 } }
  Rule { Widget: Dialog, Style { Corner_Radius: small } }
  Rule { Widget: Fab, Variant: surface, Style { Corner_Radius: 8 } }
}
```

Shapes are `none`, `extra_small`, `small`, `medium`, `large`, `extra_large` and `full` (a pill or a circle: half the node's
shorter side), or a number; an elevation is a level from 0 to 5.

A theme's `Components` sets the corner radius and elevation of a widget made in Python with `tess_ui.widgets`,
by MD3 component and variant. It is not read by a view, which takes its shape from its rules.

```tdl
Theme {
  Components {
    Card { Elevated { Corner_Radius: 4, Elevation: level_5 } }
    Dialog { Corner_Radius: small }
    Fab { Small { Corner_Radius: 8 } }
  }
}
```

```python
from tess_ui.widgets import card

card(app.window, 200, 120, variant="elevated")     # corner radius 4, from the theme
```

A widget's entry for its variant (`card.elevated`) is read, then its component's (`card`), over the widget's own values. A FAB's
variant is its size (`fab.small`, `fab.default`, `fab.large`). A custom theme's entry for a key replaces the default's.

## Type

A theme's `Typography` overrides fields of MD3's 15 type roles
(`display_large` to `label_small`):

```tdl
Theme {
  Typography {
    Body_Large { Font_Family: Inter, Font_Size: 17 }
    Title_Medium { Font_Weight: 600 }
  }
}
```

A `Text` or `Link` with `Typography_Role: body_large` takes the theme's `body_large`; fields the node
sets itself still win. A custom theme's entry for a role replaces the default's, rather than merging
with it. Widgets follow it too. Text inputs don't: a `TextInput` keeps its own font, so typed text isn't
restyled by the theme.

### Fonts

Three families are bundled and always available: **Roboto**, **Noto Sans Arabic** and **Hack Nerd Font
Mono**. Tesserae does not look at the system's fonts unless you ask (`App(system_fonts=True)` lets text fall back to
installed fonts for scripts the bundled ones lack, such as CJK and colour emoji), so by default text looks the same on every
machine. To use any other family, register its file first:

```python
import tess_ui

tess_ui.register_font("fonts/Inter-Regular.ttf")  # -> ["Inter"]
```

The return value is the family name to use as `Font_Family`. Naming a family that is neither bundled nor
registered draws a bundled face in its place, and Tesserae warns, naming the file and the family
(`tess_ui.fonts.FontFallbackWarning`; turn it into an error with `warnings.filterwarnings("error", ...)`).

## Making a change

| To change... | Do this |
| --- | --- |
| the app's colours | `App(theme_seed=...)`, or `Seed` in a theme |
| one colour role | `Colors` in a theme |
| every view's look | `App(stylesheet=...)`: rules |
| one kind of widget, a variant of it, or a part of it | a rule for the `Widget`, with `Variant`, `Part` or `State`, in the stylesheet |
| one view or a few nodes | `Classes` on the nodes and a rule for them; or a rule for the view's name |
| a widget's shape or shadow | `Corner_Radius` and `Elevation` in a rule (`Components` in a theme is for widgets made in Python) |
| the type | `Typography` in a theme, and [fonts](#fonts) |
| one node | its `Style` |

An app has one stylesheet, and every view it opens uses it.

### While the app runs

`app.set_theme_specs(default, custom)` re-themes every view the app opened, and the window, in one
call. Both dicts are the complete new selection (`None` for none); the seed and the light or dark
appearance stay as they are. With `run(hot_reload=True)`, saving a theme file does this for you.
`app.set_stylesheet_spec(rules)` does the same for the app's stylesheet of rules: every open view is composed again under the new rules, its state kept,
and a sheet that is wrong leaves every view as it was. With `run(hot_reload=True)`, saving the stylesheet file does this for you.

```python
from tess_ui.spec import load_theme

app.set_theme_specs(None, load_theme("themes/Dark_Theme.tdl"))
```

### Reading the theme from code

```python
theme = app.theme                      # a tess_ui.Theme
theme.role("primary")                  # (r, g, b, a)
theme.shape("card", "elevated")        # components: card.elevated, then card
theme.elevation("dialog")              # an MD3 elevation level, or None
theme.typography("body_large")         # the type role, with Typography overrides
theme.easing("emphasized_decelerate")  # (x1, y1, x2, y2), for node.animate(easing=...)
theme.duration("medium2")              # 300 (ms)
```

`shape` and `elevation` return `None` when the theme's `Components` doesn't mention the component, and
the widget uses its own MD3 default. MD3's easing and duration tokens are all there; `emphasized` is MD3's
single-curve form, `(0.2, 0, 0, 1)`.

### Files and checking

`load_theme` and `load_stylesheet` read a file into the dict the app takes; `App(custom_theme=)` and `App(stylesheet=)` do it for you,
and each also has a `*_spec=` form that takes a dict directly (`custom_theme_spec={"colors": {"primary": "#00FF00"}}`). Give one
form or the other. An unknown key in a theme file is found when the file is read, and the error names it:
`ValueError: themes/Brand_Theme.tdl:6:3: error: unknown field `colours`, expected one of `seed`, `dark`, `colors`, `styles`, `components`, `typography` (did you mean 'colors')`. A theme given as a dict names the argument instead (`custom_theme_spec=: unknown field ...`).

## How it is implemented

- **Resolving.** `Theme.resolve(theme_seed, dark, default_theme_spec, custom_theme_spec, contrast)` turns the five inputs
  into one `Theme`: the role table (`tokens.resolve_scheme`), the `components:` map, the type scale and the
  motion tokens. `app.theme` and `view.theme` return one.
- **Applying.** A view is built by Tesserae's own compiler: for each node it merges the layers
  (above), resolves colour roles against the scheme, and sets the result on the node. `view.set_theme`
  runs the same pass again over the nodes already built, in place, so a theme change never rebuilds a view.
- **Following.** `tess_ui.follow` keeps the widgets, controls and overlays made on an app's window
  without a `theme=`. When the app's theme or appearance changes (including the OS switching) it re-themes
  them with the app's views.
- **Files.** Tesserae reads theme and stylesheet files itself and hands the engine only data, as for views
  and images. `*_Theme.tdl` and `*_Stylesheet.tdl` say what a file is, and a file named
  for one kind is refused by the loader of another.

## The complete API

<!-- api:begin (written by tools/generate_api_docs.py) -->

### On the app

- `App.theme` *(property)*: The app's resolved theme (`tess_ui.Theme`): roles, component shape and elevation, typography, and motion tokens.
- `App.dark` *(property)*: Whether the app is showing its dark scheme right now.
- `App.dark_mode` *(property)*: `"system"` (following the OS), or the app's fixed `True`/`False`.
- `App.set_dark(dark: bool | str) -> None`: `True`/`False` fixes the app dark or light, re-theming every screen in place; `"system"` goes back to following the OS from its next switch.
- `App.set_theme_specs(default_theme_spec: Any, custom_theme_spec: Any) -> None`: Re-themes the running app in place: every view the app made.
- `App.set_stylesheet_spec(stylesheet_spec: dict[str, Any] | None) -> None`: Replaces the app's default stylesheet in place: every view the app made is re-styled, and views built later use it too.

### On a view

- `View.theme` *(property)*: This view's resolved theme (`tess_ui.Theme`).
- `View.set_theme(theme_seed: Optional[tuple[int, int, int, int]] = None, dark: bool = False, default_theme_spec: Optional[dict[str, Any]] = None, custom_theme_spec: Optional[dict[str, Any]] = None, contrast: float = 0.0) -> None`: Re-themes every node in place.
- `View.set_stylesheet(stylesheet_spec: Optional[dict[str, Any]] = None) -> None`: Replaces the stylesheet and re-styles every node in place; `None` clears it.

### `Theme`

```python
class Theme(
    seed: Optional[RGBA],
    dark: bool,
    roles: Optional[dict[str, RGBA]],
    components: dict[str, _Component] = <factory>,
    type_overrides: dict[str, dict[str, Any]] = <factory>,
    contrast: float = 0.0
) -> None
```

A resolved theme. Build one with `Theme.resolve(...)`.

- `duration(name: str) -> int`: An MD3 duration token, in milliseconds.
- `easing(name: str) -> Easing`: An MD3 easing token, as `animate(easing=...)` takes it.
- `elevation(component: str, variant: Optional[str] = None) -> Optional[float]`: A component's elevation level from `components:`, or `None`.
- `is_set` *(property)*: Whether there's a colour scheme (a seed was given somewhere).
- `resolve(theme_seed: Optional[RGBA] = None, dark: bool = False, default_theme_spec: Optional[dict[str, Any]] = None, custom_theme_spec: Optional[dict[str, Any]] = None, contrast: float = 0.0) -> 'Theme'`: Resolves a theme; raises `ValueError` for an unknown role, an unknown token in `components:` or an unknown `typography:` field.
- `role(name: str) -> Optional[RGBA]`: An MD3 colour role, or `None` without a scheme or for an unknown name.
- `shape(component: str, variant: Optional[str] = None) -> Optional[float]`: A component's corner radius from `components:`, or `None` when the theme doesn't say (the widget uses its own MD3 default).
- `spring(bounce: float = 0.0) -> Easing`: A spring easing: `bounce` from -1 to 1 (exclusive), 0 settling without overshoot, above 0 overshooting.
- `typography(role: str) -> Optional[tokens.TypeStyle]`: An MD3 type role with the theme's `typography:` overrides, or `None` for an unknown role.

### Loading files

- `load_theme(path: str | Path) -> dict[str, Any]`: Reads a theme file (`*_Theme.tdl`) into the dict `tess_re`'s `default_theme_spec=`/`custom_theme_spec=` take, for `View(...)` or for switching themes later:
- `load_stylesheet(path: str | Path) -> dict[str, Any]`: Reads a stylesheet file (`*_Stylesheet.tdl`) into the dict `tess_re`'s `stylesheet_spec=` takes.

### Tokens

`tess_ui.tokens`: Material Design 3's tokens as Python values.

- `shape(name: str) -> Optional[float]`: The corner radius of the MD3 shape token `name` (`"small"`, `"medium"`, ...
- `elevation(name: str) -> Optional[float]`: The level (0 to 5) of the MD3 elevation token `name`, or `None` if it isn't one.
- `type_style(role: str) -> Optional[TypeStyle]`: The font size, weight, line height and tracking of the MD3 type role `role`, or `None` if it isn't one.
- `color_scheme(seed: RGBA, dark: bool = False, contrast: float = 0.0) -> dict[str, RGBA]`: Every MD3 role for `seed`, light or dark.
- `baseline_scheme() -> dict[str, RGBA]`: Every role, for widgets with no theme: the engine's baseline table (`BASELINE`).
- `resolve_scheme(theme_seed: Optional[RGBA], dark: bool, default_theme: Optional[dict[str, Any]], custom_theme: Optional[dict[str, Any]], contrast: float = 0.0) -> Optional[dict[str, RGBA]]`: The scheme a view resolves roles against, by `tess_re`'s `View` rules: the seed is `theme_seed`, else the custom theme's `seed:`, else the default theme's; `colors:` overrides apply default theme first, then custom.
- `elevation_shadows(level: float) -> list[Shadow]`: MD3 elevation `level` (0–5, fractional allowed) as a `shadows` list, `(color, offset_x, offset_y, blur, spread)`: `tess_re`'s key shadow (30% black) first, so it paints on top, then its ambient shadow (15%).

- `tokens.ROLES` = `tuple of 49`
- `tokens.SHAPES` = `dict of 6`
- `tokens.ELEVATION_LEVELS` = `dict of 6`
- `tokens.TYPE_SCALE` = `dict of 15`
- `tokens.BASELINE` = `dict of 49`
### Fonts

- `register_font(path: str | Path) -> list[str]`: Reads the font file at `path` and registers it with `tess_re`, process-wide.
- `available_families() -> frozenset[str]`: Every family `tess_re` can draw right now: its bundled ones plus any registered through `register_font`.
- `FontFallbackWarning`: A `font_family` names a family that isn't bundled with `tess_re` and hasn't been registered, so `tess_re` will draw a bundled face instead.
- `BUNDLED_FAMILIES` = `['Hack Nerd Font Mono', 'Noto Sans Arabic', 'Roboto']`

<!-- api:end -->
