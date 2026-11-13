"""The built-in widgets, declared (spec section 16, the part that exists in 0.4.x; phase 3 of #209).

These are the 0.4.x `kind:` values with their properties in the new, flat form: `text: Hello` and `typography_role: title_large` instead of
`text: {content: Hello, typography_role: title_large}`, `icon: home` instead of `icon: {name: home}`. State is a property (`checked`,
`selected`, `value`), never style. The component pass (#118 to #208) adds and merges widgets; each change is a declaration here.

`widgets._load_builtins` imports this module the first time the registry is read.
"""

from __future__ import annotations

from tess_ui.spec.placement import PLACEMENTS
from tess_ui.spec.widgets import Property as P, declare

_TEXT_ALIGNS = ("start", "center", "end")
_TEXT_WRAPS = ("word", "none")
_TEXT_OVERFLOWS = ("clip", "ellipsis")

declare("Slot", doc="Where a caller's children go in a view (a default slot, or a named one).")
_DISABLED = {"disabled": P("bool", doc="Dimmed, not focusable, and its handlers do not run.")}
declare("Rect", _DISABLED, container=True, doc="A filled box that can hold children.")
declare("Container", {**_DISABLED,
                       "measured_width": P("float", model=True, doc="Output: how wide it is laid out. Bind a Signal or a state name to read it (written after layout and when the window resizes)."),
                       "measured_height": P("float", model=True, doc="Output: how tall it is laid out.")}, container=True, doc="A box with an optional fill that lays out its children.")

_TEXT = {
    "text": P("str", default="", doc="The text shown."),
    "typography_role": P("str", doc="A type role of the theme, such as body_large or title_large."),
    "font_family": P("str"),
    "font_size": P("float"),
    "font_weight": P("any"),
    "wrap": P("enum", choices=_TEXT_WRAPS, default="word", doc="'word' breaks a long line; 'none' never does."),
    "overflow": P("enum", choices=_TEXT_OVERFLOWS, default="clip"),
    "text_align": P("enum", choices=_TEXT_ALIGNS, default="start"),
    "max_lines": P("int", doc="The most lines shown, from 1; a longer text is cut (with `overflow: ellipsis`, an ellipsis ends the last line)."),
    "letter_spacing": P("float", default=0.0, doc="Extra space between letters, in pixels (tracking)."),
}
declare("Text", {**_TEXT, "selectable": P("bool", doc="The text can be selected and copied."),
                 "runs": P("list", doc="Pieces of one text in different styles, instead of `text`: each a string, or `{text, color, weight, italic, underline, strikethrough, font_size, font_family, link}`. "
                                       "A piece with a `link` is the theme's `primary` and underlined, and `on_link` runs with `event.href` when it is pressed."),
                 "heading": P("int", choices=(1, 2, 3, 4, 5, 6), doc="Makes it a heading of this level for a screen reader.")},
        extras=("foreground",), doc="A run of text.")
declare("Link", {**_TEXT, "text": P("str", default="", doc="The link's text, which names it for a screen reader."),
                 "href": P("str", doc="A web or mail link (http, https, mailto, tel) opened in the OS's browser or mail program when it is activated."),
                 "visited": P("bool", model=True, doc="Whether it has been followed; opening its href sets it, and a rule can show it with `state: visited`."),
                 "disabled": P("bool", doc="Dimmed, and not activated."),
                 "underline": P("enum", choices=("hover", "always", "never"), default="hover", doc="When the text is underlined: while the pointer is over it or it has the keyboard focus, always, or never.")},
        extras=("foreground",), doc="Text that can be activated.")
declare("TextInput", {
    "text": P("str", default="", model=True, doc="What the user has typed."),
    "placeholder": P("str", default="", doc="Shown, dimmed, while the field is empty."),
    "multiline": P("bool", doc="Several lines; Enter makes a new one."),
    "obscured": P("bool", doc="Shows dots instead of the text, and blocks copy and cut (a password)."),
    "max_length": P("int", default=0, doc="The most characters it takes; 0 is no limit."),
    "read_only": P("bool", doc="The text can be selected and copied but not changed."),
    "mask": P("mask", doc="A pattern the typed text is put in: # a digit, A a letter, * either, \\ a literal; other characters come by themselves."),
    "typing_effect": P("enum", choices=("none", "flash", "fade_in"), default="none",
                       doc="What happens to the characters just typed: `flash` tints them with the primary colour for a moment; `fade_in` fades them in out of the background."),
    "typing_duration": P("float", minimum=0, doc="How long a flash or a fade-in lasts, in milliseconds: 260 for a flash and 180 for a fade-in when left out; 0 leaves the effect out."),
    "flash_color": P("color", doc="What a flash is tinted with: a theme role or a colour (`primary@50%` works); the primary colour when left out."),
    "flash_opacity": P("float", minimum=0, maximum=1, doc="How strong a flash starts, from 0 to 1: 0.24 when left out."),
    "caret_effect": P("enum", choices=("none", "glide"), default="none",
                      doc="`glide` draws the caret itself and eases it to each new place; it blinks, solid while typing. The engine's caret is hidden meanwhile."),
    "glide_duration": P("float", minimum=0, doc="How long the caret takes to reach its new place, in milliseconds: 120 when left out; 0 makes it jump."),
    "caret_blink": P("float", minimum=0, doc="The time the gliding caret is on and then off, in milliseconds: 530 when left out; 0 keeps it solid."),
    "typography_role": P("str"), "font_family": P("str"), "font_size": P("float"), "font_weight": P("any"), "disabled": P("bool"),
}, extras=("foreground",), doc="A bare text input (the part of a TextField that takes the typing).")
declare("Image", {
    "src": P("str", doc="A path relative to the file."),
    "fit": P("enum", default="cover", choices=("cover", "contain", "fill"), doc="How the picture fills its box."),
    "alt": P("str", doc="What the picture shows, for a screen reader. Without it the picture is decorative and hidden from one."),
    "frame": P("any", doc="A video frame, (rgba, width, height), pushed from a ViewModel."),
}, doc="A picture.")
declare("Icon", {"icon": P("icon", doc="A built-in icon name."),
                 "path": P("str", doc="SVG path data to draw instead of a named icon."),
                 "view_box": P("list", doc="[min_x, min_y, width, height] the path is drawn in; Material Symbols' 0 -960 960 960 when not given.")},
        extras=("foreground",), one_of=[("icon", "path")], doc="A glyph from the built-in set, or from SVG path data.")
declare("Canvas", {"draw": P("list", doc="Drawing commands in order: rect, circle or path, each with a color.")}, doc="A drawing surface: rects, circles and paths from data.")
declare("Svg", {"src": P("str", doc="A .svg or .svgz file, relative to the view."), "content": P("str", doc="The SVG text, instead of a file."),
                "alt": P("str", doc="What the picture shows, for a screen reader. Without it the picture is decorative and hidden from one.")},
        extras=("foreground",), one_of=[("src", "content")], doc="A vector picture.")
declare("ScrollView", {
    "orientation": P("enum", choices=("vertical", "horizontal"), default="vertical", doc="Which way it scrolls. Horizontal lays its children out in a row and `scroll_direction` is 'right' or 'left'."),
    "snap": P("enum", choices=("none", "start", "center", "end"), default="none", doc="When scrolling stops it settles on the nearest child that has a `snap_align` style, with that edge of the child at the same edge of the view."),
    "scroll_offset": P("float", default=0.0, model=True, doc="The scrolled distance; scrolling writes it back to a Signal it is bound to."),
    "at_top": P("bool", model=True, doc="Output: whether it is scrolled to the start. Bind a Signal or a state name to read it."),
    "at_end": P("bool", model=True, doc="Output: whether it is scrolled as far as it goes."),
    "scroll_direction": P("str", model=True, doc="Output: 'down' or 'up' (a horizontal one: 'right' or 'left') for the last scroll, 'none' before the first."),
}, container=True, doc="A scrolling viewport for its children.")

declare("VirtualList", {
    "item_height": P("float", required=True, doc="How tall every row is, in pixels."),
    "overscan": P("int", default=3, doc="Rows built beyond each edge of what is in view."),
    "scroll_offset": P("float", default=0.0, model=True, doc="The scrolled distance; scrolling writes it back to a Signal it is bound to."),
    "at_top": P("bool", model=True, doc="Output: whether it is scrolled to the start."),
    "at_end": P("bool", model=True, doc="Output: whether it is scrolled as far as it goes."),
    "scroll_direction": P("str", model=True, doc="Output: 'down' or 'up' for the last scroll, 'none' before the first."),
}, container=True, doc="A scrolling list of equal rows that builds only the rows in view: its one child is a `for:`.")
declare("Splitter", {
    "orientation": P("enum", choices=("horizontal", "vertical"), default="horizontal", doc="horizontal puts the panes side by side, vertical one above the other."),
    "position": P("float", default=0.5, model=True, doc="How much of the room the first pane has, from 0 to 1. Dragging the handle writes it back to a Signal it is bound to."),
    "min_first": P("float", default=0.0, doc="The least the first pane can be, in pixels."),
    "min_second": P("float", default=0.0, doc="The least the second pane can be, in pixels."),
    "collapsible": P("bool", doc="A double click on the handle closes the first pane, and opens it again."),
    "label": P("str", default="Resize panes", doc="What a screen reader calls the handle."),
}, container=True, doc="Two panes with a draggable, keyboard-operable handle between them.")
declare("Overlay", {
    "open": P("bool", default=False, model=True, doc="Whether it is showing. Closing it (Escape, a press outside) writes false back to a Signal it is bound to."),
    "anchor": P("str", doc="The name of a node in this view to sit against, or `parent` for the node it is written inside; without one it sits at its own `x` and `y`."),
    "placement": P("enum", choices=PLACEMENTS, default="below", doc="Where it sits against the anchor: a side (`below`, `above`, `start`, `end`), which flips or shifts to fit, or a corner or the centre "
                                                                    "(`top_start`, `top_end`, `bottom_start`, `bottom_end`, `center`), which puts its centre on that point of the anchor and is never moved."),
    "offset": P("list", doc="`[dx, dy]` pixels added to the point it is attached to, for example `[2, -2]` to nudge a badge off a corner."),
    "flip": P("bool", default=True, doc="Whether a side placement may flip or shift to fit the window; `false` keeps it where it was asked. A corner or the centre never moves."),
    "modal": P("bool", doc="Dims the window behind it, blocks input to it, and keeps focus inside."),
    "dismissible": P("bool", default=True, doc="Escape and a press outside close it."),
    "focus_first": P("bool", default=False, doc="When it opens, the focus moves to the first thing in it that can take it (a menu's first row)."),
    "timeout": P("float", default=0.0, doc="Closes itself this many milliseconds after it opens, unless the pointer is over it; 0 never."),
}, container=True, doc="A layer over the window: a menu, a dialog, a popover. `on_dismiss` runs when it closes itself, or the user closes it.")
_CONTROL_LABEL = P("str", doc="Text beside it that is part of what you press, and what a screen reader calls it.")
declare("Checkbox", {"checked": P("bool", model=True, doc="true, false, or empty (null) for a box that is neither: a parent of some checked children."),
                     "disabled": P("bool"), "error": P("bool", doc="Drawn in the error colours."), "label": _CONTROL_LABEL},
        extras=("foreground",), doc="A box that is on or off.")
declare("RadioButton", {"selected": P("bool", model=True), "group": P("str", doc="Buttons with one group are exclusive."),
                        "disabled": P("bool"), "error": P("bool", doc="Drawn in the error colours."), "label": _CONTROL_LABEL},
        extras=("foreground",), doc="One choice of a group.")
declare("Switch", {"selected": P("bool", model=True), "disabled": P("bool"), "label": _CONTROL_LABEL,
                   "icons": P("bool", doc="A check on the handle when on and a cross when off.")}, extras=("foreground",), doc="A toggle.")
declare("Slider", {"value": P("float", default=0.0, model=True, doc="From `min` to `max`; a bound Signal follows the drag."),
                   "min": P("float", default=0.0), "max": P("float", default=1.0),
                   "step": P("float", doc="Snap to multiples of this from `min`; the keys move by it."),
                   "ticks": P("bool", doc="A mark at each step (needs `step`): a discrete slider."),
                   "value_indicator": P("bool", doc="A bubble with the value over the handle while it is dragged or has the keyboard."),
                   "vertical": P("bool", doc="Stood up: the bottom is `min`; `style.height` is its length and `style.width` the touch target's."),
                   "size": P("enum", choices=("xs", "s", "m", "l", "xl"),
                             doc="MD3 Expressive's size: a thicker track in two pieces and a thin 4 px handle (empty: the standard 4 px track and 20 px handle)."),
                   "icon": P("str", doc="An icon inset at the start of the track (needs a `size` of `s` or larger)."),
                   "label": P("str", doc="What a screen reader calls it."), "disabled": P("bool")},
        extras=("foreground",), doc="Picks a value between `min` and `max` by dragging.")
declare("RangeSlider", {"low": P("float", default=0.0, model=True, doc="The least of the two values; a bound Signal follows the drag."),
                        "high": P("float", default=1.0, model=True, doc="The most of the two values; it is never below `low`."),
                        "min": P("float", default=0.0), "max": P("float", default=1.0),
                        "step": P("float", doc="Snap to multiples of this from `min`; the keys move by it."),
                        "ticks": P("bool", doc="A mark at each step (needs `step`): a discrete slider."),
                        "value_indicator": P("bool", doc="A bubble with the value over a handle while it is dragged or has the keyboard."),
                        "vertical": P("bool", doc="Stood up: the bottom is `min`; `style.height` is its length and `style.width` the touch target's."),
                        "size": P("enum", choices=("xs", "s", "m", "l", "xl"),
                                  doc="MD3 Expressive's size: a thicker track in three pieces and thin 4 px handles (empty: the standard 4 px track and 20 px handles)."),
                        "icon": P("str", doc="An icon inset at the start of the track (needs a `size` of `s` or larger)."),
                        "label": P("str", doc="What a screen reader calls it; the handles are 'minimum' and 'maximum' of it."), "disabled": P("bool")},
        extras=("foreground",), doc="Picks two values, a least and a most, between `min` and `max` by dragging two handles.")
declare("SpinBox", {
    "value": P("float", default=0.0, model=True), "min": P("float"), "max": P("float"), "step": P("float", default=1.0),
    "disabled": P("bool"), "label": P("str", doc="What a screen reader calls it."),
    "decimals": P("int", doc="How many decimal places show (empty: only as many as the number needs)."),
    "prefix": P("str", default="", doc="Shown before the number, such as a currency sign."),
    "suffix": P("str", default="", doc="Shown after the number, such as a unit."),
    "wrap": P("bool", doc="A step past one bound lands on the other (needs min and max)."),
}, doc="A number with step buttons. Holding a button repeats the step; Page Up and Page Down step by ten.")
_TRACK = P("str", doc="The colour role of the track behind the indicator.")
declare("CircularProgress", {"value": P("float", doc="0 to 1; leave out, or give nothing, for a wait with no end."), "track": _TRACK,
                             "wavy": P("bool", doc="The arc is a wave whose crests flow round the ring (MD3 Expressive)."),
                             "thickness": P("float", doc="The ring's width in pixels (4 is the standard one; MD3 Expressive's are thicker). With a `track` the arc and the track are a gap apart."),
                             "label": P("str", doc="What a screen reader calls it.")}, extras=("foreground",), doc="A progress ring.")
declare("LinearProgress", {"value": P("float", doc="0 to 1; leave out, or give nothing, for a wait with no end."), "track": _TRACK,
                           "thickness": P("float", doc="The bar's height in pixels (4 is the standard one; MD3 Expressive's are thicker)."),
                           "buffer": P("float", doc="0 to 1: how much has loaded, drawn as a lighter bar behind the value."),
                           "stop_indicator": P("bool", doc="A dot at the end of the track (Material 3)."),
                           "wavy": P("bool", doc="The bar is a sine wave that flows along a straight track (MD3 Expressive); the control is taller by the wave's height."),
                           "two_bar": P("bool", doc="A wait with no end sweeps as two bars, a long one and a short one a little behind (MD3), not one."),
                           "label": P("str", doc="What a screen reader calls it.")}, extras=("foreground",), doc="A progress bar.")
declare("LoadingIndicator", {"contained": P("bool", doc="The shape in a `primary_container` circle, in `on_primary_container` (MD3 Expressive)."),
                             "label": P("str", doc="What a screen reader calls it.")}, extras=("foreground",), doc="An indeterminate wait indicator.")
declare("TimePickerDial", {"hour": P("float", default=0.0, model=True, doc="0 to 23; a press keeps the half of the day it is in."),
                           "minute": P("float", default=0.0, model=True, doc="0 to 59, in fives on the face."),
                           "mode": P("enum", choices=("hour", "minute"), default="hour", model=True,
                                     doc="Which hand the face shows and sets; letting go in hour mode moves on to minutes."),
                           "auto_advance": P("bool", default=True, doc="Letting go in hour mode moves on to the minutes."),
                           "label": P("str", doc="What a screen reader calls it.")},
        doc="The clock face of a time picker.")

_COLOUR_VALUE = P("str", default="#000000", model=True, doc="The colour: '#rrggbb', or '#rrggbbaa' when its alpha is below 1 (lowercase; capitals are read and written back lowercase).")
_COLOUR_HUE = P("float", model=True, doc="The hue in degrees the picker remembers for a colour with none of its own (a grey, a black), so a drag to a corner and back keeps the hue; "
                                         "bind a `state:` name shared by the area and the hue strip.")
_COLOUR_LABEL = P("str", doc="What a screen reader calls it.")
declare("ColourArea", {"value": _COLOUR_VALUE, "hue": _COLOUR_HUE, "label": P("str", default="Saturation and value", doc="What a screen reader calls it."), "disabled": P("bool")},
        doc="A square of saturation (across) and value (up) for the colour's hue, with a handle: drag it, or move it with the arrow keys (Shift for a bigger step).")
declare("ColourStrip", {"channel": P("enum", choices=("hue", "alpha"), default="hue", doc="`hue` is the rainbow, 0 to 360 degrees; `alpha` is clear to the colour over a chequerboard, 0 to 100 percent."),
                        "value": _COLOUR_VALUE, "hue": _COLOUR_HUE, "label": _COLOUR_LABEL, "disabled": P("bool")},
        doc="A strip with a handle that picks a colour's hue or its alpha: drag it, or use the arrow, Page Up, Page Down, Home and End keys.")
declare("ColourField", {"channel": P("enum", choices=("hex", "red", "green", "blue", "alpha"), default="hex",
                                     doc="`hex` takes '#rrggbb' or '#rrggbbaa'; the others take a whole number from 0 to 255."),
                        "value": _COLOUR_VALUE, "label": _COLOUR_LABEL, "disabled": P("bool")},
        doc="A text field for the colour. A valid entry sets `value` at once; an invalid one leaves it and shows the field in the error colours.")
declare("ColourSwatches", {"roles": P("list", doc="The theme colour roles to show, in order (primary, secondary, tertiary, error, surface, on_surface, primary_container and secondary_container when left out)."),
                           "value": _COLOUR_VALUE, "label": P("str", default="Theme colours", doc="What a screen reader calls the row."), "disabled": P("bool")},
        doc="A row of the theme's colour roles; pressing one sets `value` to its colour.")

_FB_OUT = "Output: written to the name it is bound to."
declare("FileBrowser", {
    "mode": P("enum", choices=("open", "save", "folder"), default="open", doc="`open` picks existing files, `save` a folder and a name, `folder` a folder."),
    "multiple": P("bool", doc="More than one file (or folder) may be picked."),
    "start": P("str", default="", doc="The folder it opens in; the root, else the working folder, when left out."),
    "root": P("str", default="", doc="A folder it never leaves: nothing above it can be entered."),
    "filters": P("list", default=[], doc="The file types: each {label, patterns: [glob, ...]}; an `All files` choice is added."),
    "open": P("bool", doc="Whether the dialog is showing: going true makes a new browser at `start`; nothing is read from the disk before."),
    "initial": P("str", default="", doc="The file name a save starts with."),
    "rows": P("int", default=8, doc="How many rows the list shows at once (for Page Up and Page Down and for scrolling the cursor into view)."),
    "row_height": P("float", default=40.0, doc="How tall a row is, in pixels."),
    "command": P("str", default="", doc="What to do, written as text that starts with a number that is new each time: `7 click 3 ctrl`, `8 key arrow_down`, `9 up`, `10 back`, "
                                         "`11 forward`, `12 home`, `13 refresh`, `14 goto` (the text in `path`), `15 open 3`, `16 accept`, `17 new_folder Name`, `18 confirmed`."),
    "path": P("str", default="", model=True, doc="The text of the path bar: it follows the folder, and `goto` goes to what was typed."),
    "filename": P("str", default="", model=True, doc="The name typed in a save dialog; picking a file there puts its name here."),
    "hidden": P("bool", model=True, doc="Whether names that start with a dot are listed."),
    "filter": P("int", default=0, model=True, doc="The number of the file type in use."),
    "scroll": P("float", default=0.0, model=True, doc="The list's scroll offset: bind the list's `scroll_offset` to the same name; moving the cursor writes the offset that shows it."),
    "confirm": P("bool", model=True, doc="A save of a file that is there is waiting for a yes; the view writes false to cancel it."),
    "entries": P("list", model=True, doc=_FB_OUT + " The rows shown: {name, path, dir, icon, size, modified, hidden}, folders first."),
    "selection": P("list", model=True, doc=_FB_OUT + " The paths picked."),
    "cursor": P("int", model=True, doc=_FB_OUT + " The row the keyboard is on, or -1."),
    "folder": P("str", model=True, doc=_FB_OUT + " The folder being shown."),
    "crumbs": P("list", model=True, doc=_FB_OUT + " The folder as a trail: each {name, path}."),
    "message": P("str", model=True, doc=_FB_OUT + " What last went wrong, such as a folder that cannot be read; empty when nothing has."),
    "valid": P("bool", model=True, doc=_FB_OUT + " Whether OK may be pressed."),
    "target": P("list", model=True, doc=_FB_OUT + " The paths OK would give."),
    "chosen": P("str", model=True, doc=_FB_OUT + " The name (the last part) of the first of `target`."),
    "exists": P("bool", model=True, doc=_FB_OUT + " A save whose file is there already."),
    "problem": P("str", model=True, doc=_FB_OUT + " Why the save name will not do."),
    "can_back": P("bool", model=True, doc=_FB_OUT), "can_forward": P("bool", model=True, doc=_FB_OUT), "can_up": P("bool", model=True, doc=_FB_OUT),
    "filter_items": P("list", model=True, doc=_FB_OUT + " The file types as menu items: {value, label}."),
}, doc="The file dialog's mind: it draws nothing. It reads folders through `tess_ui.filesystem`, keeps the history, the selection and the rules, and tells the view through the names it is bound to.")

_MIND_OUT = "Output: written to the name it is bound to."
_MIND_COMMAND = "What to do, written as text that starts with a number that is new each time (`7 key arrow_down`): "
declare("IconBrowser", {
    "value": P("str", default="", model=True, doc="The icon: a built-in icon's name, or the file name (with its extension) of one in `folder`. A pick writes it."),
    "open": P("bool", default=True, doc="Whether the grid is listed: going true reads `folder`; nothing is read before. `current` is kept either way."),
    "folder": P("str", default="", doc="A folder of `.svg` and `.png` files to offer besides the built-in icons; read through `tess_ui.filesystem`."),
    "query": P("str", default="", doc="The search text: an icon is kept when its name has every word of it (`arrow back` finds `arrow_back`)."),
    "columns": P("int", default=8, doc="How many icons are in a row (for the arrow keys and the rows of `grid`)."),
    "rows": P("int", default=6, doc="How many rows show at once (for Page Up and Page Down and for scrolling the cursor into view)."),
    "row_height": P("float", default=48.0, doc="How tall a row is, in pixels."),
    "command": P("str", default="", doc=_MIND_COMMAND + "`key arrow_down ctrl`, `key arrow_up field` (from the search field), `click 12`, `refresh`."),
    "scroll": P("float", default=0.0, model=True, doc="The grid's scroll offset: bind the list's `scroll_offset` to the same name; moving the cursor writes the offset that shows it."),
    "grid": P("list", model=True, doc=_MIND_OUT + " The results in rows; each row {key, cells}, a cell {index, name, kind (glyph, svg, png or file), icon, svg, frame}."),
    "cursor": P("int", model=True, doc=_MIND_OUT + " The cell the keyboard is on, or -1."),
    "count": P("int", model=True, doc=_MIND_OUT + " How many icons the search found."),
    "current": P("any", model=True, doc=_MIND_OUT + " The cell of `value`, for the swatch that opens the picker (kind `none` when it is not an icon the picker knows)."),
    "message": P("str", model=True, doc=_MIND_OUT + " What last went wrong, such as a folder that cannot be read; empty when nothing has."),
    "disabled": P("bool"),
}, doc="The icon picker's mind: it draws nothing. It lists the built-in icons and the files of a folder, searches them, keeps the cursor, reads the previews of the files in view and tells the view through the names it is bound to.")

declare("FontBrowser", {
    "value": P("str", default="", model=True, doc="The font family: a pick writes it."),
    "open": P("bool", default=True, doc="Whether the list is built: going true makes it; nothing is listed before. `mode` and `current` are kept either way."),
    "query": P("str", default="", doc="The search text: a family is kept when its name has every word of it, without regard to case."),
    "rows": P("int", default=8, doc="How many rows show at once (for Page Up and Page Down and for scrolling the cursor into view)."),
    "row_height": P("float", default=40.0, doc="How tall a row is, in pixels."),
    "command": P("str", default="", doc=_MIND_COMMAND + "`key arrow_down`, `key arrow_up field` (from the search field), `click Fira Sans`."),
    "scroll": P("float", default=0.0, model=True, doc="The list's scroll offset: bind the list's `scroll_offset` to the same name; moving the cursor writes the offset that shows it."),
    "entries": P("list", model=True, doc=_MIND_OUT + " The families that match the search, each {family, loadable}: `loadable` says the engine can draw text in that family."),
    "cursor_name": P("str", model=True, doc=_MIND_OUT + " The family the keyboard is on, or empty."),
    "count": P("int", model=True, doc=_MIND_OUT + " How many families the search found."),
    "mode": P("str", model=True, doc=_MIND_OUT + " Empty until it has asked for the families, then `list`, or `text` when they cannot be listed (no `fc-list`, or it failed): the view then offers a text field."),
    "message": P("str", model=True, doc=_MIND_OUT + " Why the families cannot be listed; empty when they can."),
    "current": P("any", model=True, doc=_MIND_OUT + " The row of `value`: {family, loadable}, for the button of a closed popup."),
    "disabled": P("bool"),
}, doc="The font list's mind: it draws nothing. It asks `tess_ui.font_families` for the installed families, searches them, keeps the cursor and tells the view through the names it is bound to.")

declare("ChordRecorder", {
    "value": P("str", default="", model=True, doc="The key chord as text, `Ctrl+Alt+Shift+Meta+Key` (modifiers in that order, the key last, a named key in title case): `Ctrl+Shift+F1`. Empty is no shortcut. Recording and a committed typed text write it, in that form."),
    "draft": P("str", default="", model=True, doc="The text of the field the chord is typed in: the control sets it to the chord after a recording or a commit, and the view's field writes it as the person types. Nothing is read from it until `typed`."),
    "recording": P("bool", default=False, model=True, doc="Whether the next key press is recorded as the chord. The view sets it true to start; a finished or cancelled recording writes false."),
    "command": P("str", default="", doc=_MIND_COMMAND + "`key arrow_left ctrl shift` (a key the button heard, then the modifiers held), `typed ctrl+shift+f1` (a text committed in the field), `record`, `stop`."),
    "preview": P("str", model=True, doc=_MIND_OUT + " While recording, the modifiers held so far, such as `Ctrl+Shift+`; otherwise empty."),
    "invalid": P("bool", model=True, doc=_MIND_OUT + " The value is not a key chord, or the text typed was not one."),
    "message": P("str", model=True, doc=_MIND_OUT + " Why `invalid`, or why a key could not be recorded; empty when nothing is wrong."),
    "disabled": P("bool"),
}, doc="The key-chord field's mind: it draws nothing. It records a key press as a chord, reads a typed chord and writes it in the canonical form, and tells the view through the names it is bound to.")

declare("NodeGraph", {"edges": P("list", doc="The links: each {from: id, to: id}, the ids of the GraphNodes."),
                      "snap": P("float", default=0.0, doc="A node the user moves lands on a multiple of this many pixels; 0 is no grid."),
                      "arrows": P("bool", doc="Each edge ends in an arrowhead."),
                      "fit": P("bool", doc="Pan and zoom, when it opens, so every node shows (never beyond actual size).")},
        container=True, doc="A canvas of linked nodes you can pan, zoom and move.")
declare("GraphNode", {"label": P("str"), "x": P("float"), "y": P("float")}, container=True, doc="A node of a NodeGraph.")

declare("Window", {
    "title": P("str", required=True, doc="The OS window's title."), "borderless": P("bool", default=False),
    "remember": P("any", doc="true, or a name: the window's size, place (where the platform lets an app say) and maximized state are kept between runs."),
    "fullscreen": P("bool", doc="The window fills its monitor, borderless (set when the view loads)."),
    "maximized": P("bool", doc="The window opens maximized."),
    "transparent": P("bool", doc="A see-through window that draws only what the view paints; the OS fixes it before the window opens."),
    "blur_behind": P("bool", doc="The desktop behind a transparent window is blurred (where the compositor does it)."),
    "click_through": P("bool", doc="Clicks go to the window beneath; the window takes none."),
    "min_width": P("float"), "min_height": P("float"), "title_bar": P("dict", doc="Title, icon and buttons of a custom title bar."),
}, container=True, doc="The root of an app window.")
declare("TitleBar", {"title": P("str"), "icon": P("icon"), "buttons": P("list")}, container=True, doc="A custom title bar.")
declare("Dock", {"closed": P("list", model=True, doc="The names of the closable panels that are shut; a close button adds its panel, and taking a name out opens the panel again.")},
        container=True, doc="Panels docked around a centre.")
declare("DockPanel", {"title": P("str", doc="The panel's tab, when its zone has several."),
                      "closable": P("bool", doc="Its tab has a close button.")}, container=True, doc="One panel of a Dock.")
