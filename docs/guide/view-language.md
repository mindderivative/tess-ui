# The View Language

A view is a TDL file that says what is on the screen and how it reacts. One shape does everything: a **node**, a block headed by its widget, holding
the properties of that widget, a `Children` block of nodes, and a few keys every node has. This page is the whole language; the rest of the
guide pages are about the widgets and the app around it. TDL itself (blocks, properties, lists, comments, the `<| |>` slot) is described in the
[TDL language reference](https://github.com/mindderivative/tess-dl); this page is what Tesserae reads in it.

```text title="Counter_View.tdl"
---
TDL: 0.2
Name: counter
Tesserae: "0.6"
---
Container {
  Name: counter
  Style { Flex_Direction: vertical, Width: 240, Height: 120, Gap: 12, Padding: 16 }
  Children {
    Text {
      Typography_Role: title_large
      Text: Count: <| count |>
      Style { Width: 200, Height: 32, Foreground: on_surface }
    }
    Rect {
      Name: add
      Style { Width: 120, Height: 40, Background: primary, Corner_Radius: 8 }
      Handlers { On_Click: increment }
      A11y { Label: Add one }
    }
  }
}
```

Every file starts with a metadata block between `---` lines: `TDL: 0.2` (the language), `Name` (the view's name) and `Tesserae: "0.6"`, the release series it
is written for ([the metadata](naming-convention.md#the-metadata-block)). The root block is the root node. Files are named `<Name>_View.tdl` and found by name in `Views/` or a folder the app searches
([Projects](projects.md)). A view with `Params` is a component: another view calls it by its name, with the params as plain keys. There is no other difference.

## The shape of TDL

- **Keys are `Title_Case`**: each part between underscores has a capital (`typography_role` is `Typography_Role`, `on_click` is `On_Click`, `a11y` is `A11y`). This page and the
  others write a key that way wherever it is a key. Values are never changed: `filled`, a widget name, a `Name` and the text of a string are written as they are.
- **A node is a block headed by its widget**: `Button { ... }`. A scalar key is a property (`Label: Save`, `Disabled: true`, `Width: 100`); a list of scalars is
  `Choices: [filled, tonal]`.
- **A map value is a block headed by its key**: `Style { Flex_Direction: horizontal }`, `A11y { Role: button }`. A block that holds nothing but `Item` blocks is a list of
  maps (a tooltip's `Actions`, rich text's `Runs`).
- **`Children { }` holds the child nodes**, in order. A block directly inside `Children`, `If` or `For` is a node; any other block inside a node is a map.
- **An expression is a slot**, `<| expression |>`. A value that is exactly one slot is that expression (`Disabled: <| not ready |>`); text around slots is a template
  (`Text: Battery <| level |>%`); a quoted string is plain text, and a `<|` inside quotes is text too. A `{{ }}` in a `.tdl` file is refused.
- A comment runs from `#` to the end of the line.

## Nodes

| Key | Meaning |
|---|---|
| the block's head | which widget: a built-in, one the app registered, or a view found by name |
| `Name` | an optional handle, unique in the view (a letter or `_`, then letters, digits and `_`) |
| `If`, `For` | wrappers around a node: include it while an expression is true; repeat it for each element ([below](#repeating-choosing-and-remembering)) |
| `Slot` | which slot of the view being called a child goes into |
| `State` | local state: names with starting values |
| `Style` | layout and paint, and the extras the widget declares |
| `Classes` | extra names a stylesheet rule can select |
| `Handlers` | events to actions |
| `A11y` | accessibility: `Label`, `Role`, `Hidden`, `Live`, `Level`, `Expanded`, `Selected`, `Checked`, `Value`, `Value_Min`, `Value_Max`, `Value_Step` |
| `Interaction` | the hover, focus and press feedback: `true`, `false` or a colour role |
| `Visible` | `false` hides the node and takes it out of layout, `true` shows it; an expression is allowed. A widget or view that declares a `Visible` property of its own keeps it |
| `Window_Region` | `drag` or `none`, for a custom title bar |
| `Route` | on a view call inside a window: makes it a screen |
| `Focus_Group` | `horizontal`, `vertical` or `both`: the focusable nodes under it share one tab stop and the arrow keys move among them |
| `Children` | child nodes |
| anything else | a **property** of the widget |

An unknown key or property is an error that names the file, line and column and suggests the nearest one:

```text
Main_View.tdl:10:7: error: Rect: no property 'colour' (properties: disabled)
```

A key that is not `Title_Case` (`typography_role`, `MaxLines`) is an error that says what to write (`write 'Typography_Role'`).

Nodes have **ids**, assigned by the loader and never written: the path from the root, using a node's `Name` where it has one
(`root.add`) and its place where it does not (`root.children[0]`), with `[key]` added under a `For`. Give a node a `Name` when something has to
find it again: a ViewModel, a stylesheet rule, a test, or a hot reload that should keep its state.

## Widgets and properties

Every widget declares its properties: a type, a default, the values it allows, whether it is required and whether the user edits it (a
**model** property). A value is a literal or an expression, and an expression's result is checked against the type.

| Widget | Properties |
|---|---|
| `Container`, `Rect` | they hold children (a `Rect` is the usual clickable box); `Disabled`. A `Container` also has `Measured_Width` and `Measured_Height`, outputs bound like `At_Top`: the size it was laid out at |
| `Text`, `Link` | `Text`, `Typography_Role`, `Font_Family`, `Font_Size`, `Font_Weight`, `Wrap`, `Overflow`, `Text_Align`, `Max_Lines`, `Letter_Spacing`; a `Text` also `Selectable`, `Runs` ([styled pieces](rich-text.md)) and `Heading`, a `Link` also `Href`, `Visited` (model), `Disabled` and `Underline` |
| `TextInput` | `Text` (model), `Placeholder`, `Multiline`, `Obscured`, `Max_Length`, `Read_Only`, `Typography_Role`, `Font_Family`, `Font_Size`, `Font_Weight`, `Disabled`, `Mask` and the [typing effects](../components/text-fields.md) (`Typing_Effect`, `Typing_Duration`, `Flash_Color`, `Flash_Opacity`, `Caret_Effect`, `Glide_Duration`, `Caret_Blink`) |
| `TextField` | the Material text field, a view Tesserae ships: see [Text fields](../components/text-fields.md) |
| `Icon` | `Icon` (a built-in icon name, or `Path` and `View_Box`: one of them) |
| `Image`, `Svg` | `Src`, `Fit`, `Alt`, `Frame` (a picture pushed in as bytes); `Src`, `Content`, `Alt` |
| `Checkbox` | `Checked` (model), `Disabled`, `Error`, `Label` |
| `Switch` | `Selected` (model), `Disabled`, `Label`, `Icons` |
| `RadioButton` | `Selected` (model), `Group`, `Disabled`, `Error`, `Label` |
| `Slider`, `RangeSlider` | `Value` (model; `Low` and `High` for a `RangeSlider`), `Min`, `Max`, `Step`, `Ticks`, `Value_Indicator`, `Vertical`, `Size`, `Icon`, `Label`, `Disabled` |
| `SpinBox` | `Value` (model), `Min`, `Max`, `Step`, `Decimals`, `Prefix`, `Suffix`, `Wrap`, `Label`, `Disabled` |
| `CircularProgress`, `LinearProgress`, `LoadingIndicator` | `Value`, `Track`, `Thickness`, `Wavy` and more: see [Progress indicators](../components/progress-indicators.md) |
| `TimePickerDial` | `Hour`, `Minute`, `Mode` (model), `Auto_Advance`, `Label` |
| `FileBrowser` | the file dialog's mind, which draws nothing: see [File dialog](../components/file-dialogs.md) (`FileDialog` is the view you call) |
| `IconBrowser` | the icon picker's mind, which draws nothing: see [Icon picker](../components/icon-pickers.md) (`IconPicker` is the view you call) |
| `FontBrowser` | the font list's mind, which draws nothing: see [Font list](../components/font-lists.md) (`FontList` is the view you call) |
| `ChordRecorder` | the key-chord field's mind, which draws nothing: see [Key chord field](../components/key-chord-fields.md) (`KeyChordField` is the view you call) |
| `ListModel` | the list editor's mind, which draws nothing: see [List editor](../components/list-editors.md) (`ListEditor` is the view you call) |
| `TokenList` | the token button's mind, which draws nothing: see [Token button](../components/token-buttons.md) (`TokenButton` is the view you call) |
| `ColourArea`, `ColourStrip`, `ColourField`, `ColourSwatches` | `Value` (model, a colour as `'#rrggbb'` or `'#rrggbbaa'` text; the picker's parts), `Hue` (model; the area and the strip), `Channel` (strip and field), `Roles` (swatches), `Label`, `Disabled`: see [Colour picker](../components/colour-pickers.md) |
| `Splitter`, `Canvas`, `VirtualList`, `Overlay` | their own sections below |
| `ScrollView`, `NodeGraph`, `GraphNode` | a scrolling box; a canvas of linked nodes; a node of it |
| `Window`, `TitleBar`, `Dock`, `DockPanel` | see [Windows, Docks & Embedded Views](windows-and-docks.md); written as the node's block in a view opened with `app.open_view`, a `Window` root sets the OS window (title, borderless, minimum sizes) and a title bar's buttons, dimming and glyphs follow the app |
| `Slot` | where a calling view's children go |

State is a property (`Checked`, `Selected`, `Value`, `Disabled`), never a style. `Foreground` is a style extra of the widgets that draw text or
glyphs, indicators and controls (`Text`, `Link`, `TextInput`, `Icon`, `Svg`, `LoadingIndicator`, `LinearProgress`, `CircularProgress`, `Checkbox`, `RadioButton`, `Switch`, `Slider`, `RangeSlider`); anywhere else it is an error that names who accepts it.

## Expressions

Everything inside `<| |>` is one expression in a safe subset of Python (TEL, the Tesserae expression language): arithmetic, comparisons, `and`/`or`/`not`, `x if c else y`, f-strings,
lists, dicts, comprehensions, indexing, and a short list of functions and methods (`len`, `min`, `max`, `sum`, `round`, `sorted`, `str`,
`format_number`, `pluralize`, `clamp`, the date functions `date_add_days`, `date_weekday`, `days_in_month`, `format_date` and `current_date`, the usual text and list methods). Nothing else runs: no imports, no attribute that starts with `_`, no
calling an object's own methods, and every expression has limits on size, steps and the numbers it may make. The text of a slot is handed to the expression
language as written, so braces, quotes and `#` inside it need no care. See [Bindings](bindings.md) for the full list.

A **Signal reads as its value**: `<| count |>` and `<| count.get() |>` are the same, and the property follows the Signal. A value that cannot
change (only literals, params with fixed values, loop variables over a fixed list) is worked out once when the view is built.

Names are looked up in the loop variables, then the local state, then the params of the view the expression is written in, then the
ViewModel, then the app (`app.current_screen`), then the built-in functions. `hovered`, `focused` and `pressed` are the interaction state of the
nearest widget with `Interaction`.

## Views calling views

```text title="Card_View.tdl"
---
TDL: 0.2
Name: Card
Tesserae: "0.6"
---
Container {
  Params {
    Title { Type: str, Required: true }
    Variant { Type: enum, Choices: [elevated, outlined], Default: elevated }
  }
  Children {
    Text {
      Name: heading
      Text: <| title |>
      Typography_Role: title_medium
      Style { Foreground: on_surface }
    }
    Slot { }
    Slot { Name: actions }
  }
}
```

`Params` is a list of names (`Params: [title, icon]`, each required unless written `Icon { Default: null }`) or a block of names, each with a type or
`{ Type, Default, Choices, Required, Model, Doc, Min, Max }`. The types are `str int float bool color length icon enum list dict node nodes handler mask any`.
`Min` and `Max` bound an `int` or a `float`: a value outside them, written at a call or worked out by an expression, is an error that names the
parameter and the range (`Flash_Opacity { Type: float, Min: 0, Max: 1 }`).

A call gives the params as keys, and its `Children` are the slot content. An expression written at the call is read **where it is written**,
in the caller's names, and it stays reactive inside the view. The view cannot see the caller's names. Children go in the default `Slot`, or in
the one named by their `Slot` key; a view with no slot takes no children.

A call's own `Style`, `Classes`, `A11y`, `Interaction` and `Handlers` lie over the called view's root, and a handler written at the call runs in
the caller's names. A view may call itself (a tree), to a depth of 64.

A param of type `handler` takes the caller's action name or statements, read in the caller's names. At a call the param is a property whose value is the text
(`On_Remove: "remove(item.id)"`), or a block of steps; the view runs it by calling the param like an action, `on_remove()`; a param the caller left out does nothing when called.
A handler param is called with no arguments: if the caller needs a value, it writes it in its own text (`On_Remove: "remove(item.id)"`).

A param that is `Model: true` and is given a bare Signal (`Dark_On: <| dark |>`) passes the Signal itself, so the view's own `Switch` edits the
caller's value.

## Repeating, choosing and remembering

`If` and `For` are blocks that wrap one node:

```text title="Rows_View.tdl"
---
TDL: 0.2
Name: Rows
Tesserae: "0.6"
---
Container {
  State { Open: false }
  Children {
    For row In <| rows |> Key <| row.id |> {
      Text {
        Name: row
        Text: <| row.title |>
        Handlers { On_Click { Call { Action: open_row, Args: [<| row.id |>] } } }
      }
    }
    If <| len(rows) == 0 |> {
      Text { Text: Nothing here }
    }
    Rect {
      Name: toggle
      Style { Width: 40, Height: 40, Background: primary }
      Handlers { On_Click { Set { Target: open, Value: <| not open |> } } }
    }
  }
}
```

- `For x In <| xs |> Key <| k |> { node }` repeats the node; it takes `item In items`, or `i, item In <| enumerate(items) |>`. The loop variable is in scope for the node, its children and its handlers.
  A `For` must write a `Key`; `Key <| None |>` says it has none. If the iterable reads something that can change, the loop is **reactive and needs a key**: when the list is replaced, nodes whose key
  stays are kept, new keys are built, removed keys are gone, and the order follows the list. A list changed in place is not noticed; replace it.
- `If <| condition |> { node }` builds the node only while its expression is true, and a node under a false `If` runs nothing. A node that needs both has the `For` outside and the `If` inside, so the `If` is
  tested for each element. An `If` or a `For` holds exactly one node, and an `If` has no `Else`: write a second `If` with the opposite condition.
- The wrappers are not part of the tree: the node under them has the same id, path and `Name` it would have without them, so a stylesheet rule, a hot reload and a test see the node only. They are
  written among nodes (in `Children`, or inside another wrapper).
- `Visible` hides a node that is built: it takes no room and no pointer, but it stays in the tree with its `State`, its running timers and its
  listeners, and showing it again is instant. Use `Visible` for something that comes and goes (a panel, a hint) and `If` for something that is not
  worth keeping while it is away. On a view call it hides the whole view; on the root of a view file it is an error (write it where the view is called).
  Focus and the accessibility tree follow the engine's hidden nodes; nothing here changes them.
- `State` makes a Signal for each name, for this node and everything under it. A starting value may be an expression over the view's own params, which seed it once when the state is made (`State { Draft: <| hour |> }`); it may not read a ViewModel's names. It belongs to the node (to each row under a `For`), and is written
  by handlers, and survives a [hot reload](hot-reload.md#a-view-written-with-widget-nodes) for a node that keeps its name or position. Use it for presentation (open, on); what the app cares about belongs
  in the ViewModel. [Two-way properties](#two-way-properties) says what it keeps on a reload.
- `For`, `If` and `Slot` are not allowed on the root of a view.

## Handlers

`Handlers` holds one block or one property for each event. A bare action name is a property; anything else is a block of **steps** that run in order, each seeing the writes of the earlier ones:

```text
Handlers {
  On_Click: save                                  # a ViewModel method
  On_Hover_Enter { Set { Target: hint, Value: <| 'Save' |> } }   # an assignment
  On_Change {                                     # several steps, in order
    Set { Target: query, Value: <| event.value |> }
    Set { Target: page, Value: <| 0 |> }
  }
  On_Tap: window.close                            # a built-in action
}
```

- `Set { Target: name, Value: <| expression |> }` assigns to local state or a ViewModel Signal. `Target` is one plain name, and `Value` is one pure expression: there is no assignment inside an expression
  and no `;`. To add to a count, write the operation out: `Value: <| count + 1 |>`.
- `Call { Action: name, Args: [<| expression |>, ...] }` calls a ViewModel method or a built-in action (a dotted name: `window.close`, `surface.dismiss`, `navigate.back`, `navigate.Settings`). `Args` are
  expressions; any other property of the step is a keyword argument (`Call { Action: pick, Args: [<| row['ref'] |>], Index: <| i |> }` calls `pick(row['ref'], index=i)`). `Call { Action: x }` alone calls `x()`.
  A call may be of a built-in like `focus`: `Call { Action: focus, Args: [<| 'name' |>] }` gives the focus to the node of that name in the view the handler is written in.
  `navigate_to(screen)` goes to a screen held in a name.

An event is one of `On_Click`, `On_Hover_Enter`, `On_Hover_Exit`, `On_Change`, `On_Focus_Enter`, `On_Focus_Exit`, `On_Tap`, `On_Long_Press`,
`On_Pan`, `On_Pinch`, `On_Touch_Start`, `On_Touch_Move`, `On_Touch_End`, `On_Touch_Cancel`, `On_File_Hover`, `On_File_Hover_Cancel`,
`On_File_Drop`, `On_Link`, `On_Input` (a slider moving, drag or key), `On_Dismiss` (an overlay closed by Escape, an outside press, its timeout or `surface.dismiss`), `On_Key` (a key pressed), `On_Submit` (Enter in a field that is not multiline), `On_Press` (the pointer pressed on the node or
anything in it; unlike `On_Click` it does not make the node a button), `On_Move` (the pointer moved over it, or anywhere while it holds the pointer) and `On_Release` (the button let go); a misspelt one is an error.
`event` is in scope in an expression. Assigning to a plain param, a loop variable or
anything else that is not writable is an error, found when the view loads ([what a handler may assign](#two-way-properties)); so is a `Set` whose `Target` is not a plain name. A `Set` is to one plain name (`Target: done`): there is
no `row.done` or `items[0]`, so change a list by assigning a new one (`Value: <| [x for x in items if x != row] |>`). A disabled node's handlers do not run.

The steps are turned back into the handler text the runtime takes (`query = event.value; page = 0`), so a mistake inside an expression points at the event's block in the file, not at the column inside the step.

### Timers

`after(ms, action)` runs `action` once after `ms` milliseconds; `every(ms, action)` runs it every `ms` until cancelled. `action` is text, run in the
scope the handler was written in: an action name (`'bump'`) or statements (`'shown = False'`). A third argument names the timer so `cancel('name')`
can stop it, and starting one of the same name again restarts it (a hover delay, a debounce). A name belongs to the scope that wrote it, as a local
name does: two items of a `For` each have their own. A timer stops when its view closes or the widget that started it is gone. Times are
frame-quantized: a timer fires on the first frame after its time is up. A mistake in a literal action text (a syntax error, a call to an unknown function or action, a name that cannot be written) is found when the view loads, at the handler's position, as it is for the handler itself. A bare action name that does not exist (`On_Click: nothere`) is reported by `app.check()`.

```text
Handlers {
  On_Click {
    Set { Target: shown, Value: <| True |> }
    Call { Action: after, Args: [<| 2000 |>, <| 'shown = False' |>, <| 'dismiss' |>] }
  }
  On_Hover_Exit { Call { Action: cancel, Args: [<| 'dismiss' |>] } }
}
```

For Python, `tess_ui.timers.Timers(window)` has the same `after`, `every`, `cancel` and `cancel_all`, each taking a function where the view takes action text.

## Scrolling

A `ScrollView` draws its `Scroll_Offset` (pixels, 0 or more; tess_re clamps it to the content once the content has a size) and reports where it is to
whatever you bind to it, so other widgets can react. Each of these is bound the way a two-way property is, to a ViewModel Signal or a `State` name:

| Property | Meaning |
| --- | --- |
| `Scroll_Offset` | Two-way: setting the Signal scrolls, and scrolling writes the Signal. |
| `At_Top`, `At_End` | Scrolled to the start, or as far as it goes. `At_End` is false until the content has been laid out. |
| `Scroll_Direction` | `'down'` or `'up'` for the last scroll, `'none'` before the first. |

```tdl
Container {
  State { Top: true, Way: none }
  Children {
    ScrollView {
      At_Top: <| top |>
      Scroll_Direction: <| way |>
      Children { }
    }
    If <| top or way == 'up' |> {              # a bar that hides while the list scrolls down
      Container { }
    }
  }
}
```

A view scrolls vertically, or sideways with `Orientation: horizontal`; a `ScrollView` that nothing is bound to keeps its own position.

## Input masks

`Mask` on a `TextInput` (or a `TextField`) puts what the user types or pastes in a pattern: `#` is a digit, `A` a letter, `*` a letter or digit, `\`
makes the next character a literal, and any other character is a literal that comes by itself.

```tdl
TextField {
  Label: Phone
  Text: <| phone |>
  Mask: "(###) ###-####"          # 5551234567 becomes (555) 123-4567; so does 555-123-4567
}
```

The text is read left to right and each slot takes the next character it accepts, so a paste in any format is fitted. A literal is added only
when more input follows it (`123` is `(123`, the `) ` comes with the fourth digit), so backspace is never stuck on one; one the user typed is kept; what
does not fit is dropped. The bound Signal holds the formatted text. The mask is applied to edits, not to a value a ViewModel sets, and tess_re's input
has no caret control yet, so where the caret ends up after the text is rewritten is tess_re's to decide.

## Drawing

A `Canvas` is a surface you draw on with data. `Draw` lists commands painted in order: `{rect: [x, y, width, height]}`,
`{circle: [cx, cy, radius]}` and `{path: [point, ...], width: 2}`, each with a `color` (a theme role, a CSS colour or `role@N%`). In a path the
first point is `[x, y]` and each later one is a line `[x, y]`, a quadratic `[cx, cy, x, y]` or a cubic `[c1x, c1y, c2x, c2y, x, y]`. Numbers are
logical pixels from the canvas's top-left; size the canvas with `Style`. Write `Draw` as one expression and it repaints when a Signal it reads changes. The commands are
dicts inside an expression, so their keys are the lower-case words above.

```tdl
Canvas {
  Style { Width: 120, Height: 24 }
  Draw: <| [{'rect': [0, 10, 120, 4], 'color': 'surface_variant'}, {'rect': [0, 10, 120 * progress, 4], 'color': 'primary'}] |>
}
```

### Dragging

`capture()` makes the node whose handler is running receive every pointer event until the button is let go or `release()` is called, so a drag
keeps following the pointer outside the node. `cursor('grabbing')` sets that node's pointer shape (any of tess_re's names: `default`, `pointer`, `text`, `grab`,
`grabbing`, `move`, `not_allowed`, `col_resize`, ...; `cursor(None)` puts back the one its style gives). Position and distance are in `event`
(`event.x`, `event.y`; a pan's `event.delta_x`). They act on the widget the handler is written on, so a timer's action cannot call them.

```tdl
Container {
  Handlers {
    On_Press {
      Set { Target: dragging, Value: <| True |> }
      Call { Action: capture }
      Call { Action: cursor, Args: [<| 'grabbing' |>] }
    }
    On_Move { Set { Target: x, Value: <| event.x if dragging else x |> } }
    On_Release {
      Set { Target: dragging, Value: <| False |> }
      Call { Action: release }
      Call { Action: cursor, Args: [<| None |>] }
    }
  }
}
```

### The clipboard

`copy(text)` puts text on the OS clipboard (a number is copied as text) and says whether it could; `paste()` is the text on it, or `''` when it holds none or
cannot be reached. Both work in a handler, and `paste()` can be used where a value is wanted:

```tdl
Container {
  Handlers {
    On_Click { Set { Target: ok, Value: <| copy(name) |> } }
    On_Long_Press { Set { Target: name, Value: <| paste() |> } }
  }
}
```

### Opening a link

`open_url(url)` hands a link to the OS (the default browser or mail program) and says whether it could. Only `http`, `https`, `mailto` and `tel` links
are opened: a view's text can come from anywhere, and `file:`, `javascript:` or an application's own scheme would run something rather than show a page, so
those are an error naming the call. For Python, `tess_ui.urls.open_url(url)` is the same.

```tdl
Link {
  Text: Read the docs
  Handlers { On_Click { Call { Action: open_url, Args: [<| 'https://example.com/docs' |>] } } }
}
```

## Tooltips

Any node can have a `Tooltip`. A plain one is text; a rich one adds a title, up to two actions, or both to the text, which every tooltip needs.

```text
Tooltip: Delete                                   # or a <| expression |>
```

```text
Tooltip { Title: Delete, Text: Removes the file for good, Delay: 300 }
```

```tdl
Container {
  Tooltip {
    Title: Delete
    Text: Removes the file for good
    Placement: above                                # below (the default), above, start, end, or a corner: top_start, top_end, bottom_start, bottom_end, center
    Actions {                                       # one or two text buttons; each is a handler
      Item { Label: Undo, On_Click: undo }
      Item { Label: Close, On_Click { Set { Target: hint, Value: <| 'closed' |> } } }
    }
  }
}
```

It shows next to the node after the pointer has rested on it for `Delay` milliseconds (500 by default), or at once when keyboard focus arrives (a click
that focuses it does not show it). It goes when the pointer leaves, when the node is pressed, when focus leaves or on Escape, and it never takes the
pointer or a press. A plain tooltip is the inverse surface and cannot be entered; a rich one (a title or actions) is a raised surface with the title above the text, and it
stays while the pointer moves onto it, going a moment after the pointer has left both. Pressing an action runs its handler and closes the tooltip. A touch
held in place shows it too. The text is also given to a screen reader as the node's `Description` where the node has none. A tooltip on a view call goes to
the root of the view called. The actions are for the pointer: the keyboard shows the tooltip and Escape closes it.

## Accessibility

`A11y` says what a node tells assistive technology: `Label`, `Role`, `Hidden`, `Live`, `Level`, and the states `Expanded`, `Selected`, `Checked`,
`Value`, `Value_Min`, `Value_Max`, `Value_Step`, `Pressed` (true, false or `mixed`), `Invalid`, `Busy`, `Description`, `Current` (`page`, `step`,
`location`, `date`, `time` or true), `Value_Now` and `Value_Text`. A value may be an expression. `Describedby` and `Controls` name another node of
the view by its `Name`, or a list of them.

```tdl
Container {
  Name: menu_button
  A11y { Pressed: <| open |>, Controls: menu, Description: <| hint |> }
}
```

Each is set on the node as written; `Describedby` and `Controls` become the nodes of those names in the same view. The components set the ones they mean
(a text field sets `Invalid` and `Description`).

## Moving between screens

`app.transition` sets how `navigate`, `back` and `forward` change screens; the default, `none`, is a swap, and `show()` is a jump that never animates.

| Transition | What the user sees |
| --- | --- |
| `fade_through` | the old screen fades out (90 ms), then the new one fades in and settles from 92% (210 ms) |
| `shared_axis_x`, `shared_axis_y` | the screens slide 30 px along the axis as they fade, forward one way and back the other |
| `shared_axis_z` | the old screen grows away as it fades, and the new one grows in from 80% |
| `container_transform` | the new screen grows from a node to fill its place, and going back shrinks into it |

```python
app.transition = "shared_axis_x"
app.navigate_with("detail", transition="container_transform", origin=card_node, params={"id": 3})
```

`back()` undoes how the screen it leaves was reached, and `forward()` repeats it. A navigation while one is playing finishes that one first, and an app that
reduces motion swaps at once. The screens of a window view (routed views) change the same way.

## The window and the app

`app` is readable in any expression and follows the window, so a layout can change with its size:

| Name | Meaning |
| --- | --- |
| `app.window_width`, `app.window_height` | the window's size in logical pixels |
| `app.width_class` | Material 3's window width class: `compact` (under 600), `medium`, `expanded` (840), `large` (1200) or `extra_large` (1600) |
| `app.height_class` | `compact` (under 480), `medium` or `expanded` (900) |
| `app.maximized`, `app.active` | whether the window is maximized, and has the focus |

```tdl
Container {
  Children {
    If <| app.width_class != 'compact' |> {
      Container { Name: rail, Style { Width: 80, Height: 40 } }
    }
    If <| app.width_class == 'compact' |> {
      Container { Name: bar, Style { Width: 80, Height: 40 } }
    }
  }
}
```

A ViewModel that has an `app` of its own keeps it. `tess_ui.tokens.width_class(width)` and `height_class(height)` give the classes for a size in Python.

## Long lists

A `For` builds every row it makes, which is fine for a screenful and not for ten thousand. A `VirtualList` is a scrolling list of equal-height
rows that builds only the rows in view, and more as it scrolls. Its one child is the `For`; write the row once.

```tdl
VirtualList {
  Item_Height: 48
  Overscan: 3                           # rows built past each edge (the default)
  Scroll_Offset: <| y |>                # as for a ScrollView, with At_Top, At_End and Scroll_Direction
  Children {
    For row In <| rows |> Key <| row.id |> {
      Container {
        Handlers { On_Click { Set { Target: picked, Value: <| row.id |> } } }
        Children {
          Text { Text: <| row.name |>, Typography_Role: body_large, Style { Foreground: on_surface } }
        }
      }
    }
  }
}
```

The list is as tall as all its rows, and each row built sits at its place in it, so a row's own `Style` sets its width, background and so on but not its
height or position. Rows leave and come as the list scrolls: a row's local `State` is not kept across that. Rows must all be `Item_Height` tall. Opening a
list of 10 000 builds about a dozen rows.

## Overlays

An `Overlay` shows its children in a layer over the window while `Open` is true: a menu, a popover, a dialog. It takes no room where it is written.

```tdl
Overlay {
  Open: <| menu_open |>
  Anchor: trigger            # the name of a node in this view; the layer sits against it
  Placement: below           # or above, start, end (they flip or shift to fit), or a corner: top_end, bottom_start, center...
  Offset: [0, 4]             # optional, in pixels
  Flip: true                 # false keeps the side it is given
  Style { Width: 160, Background: surface_container }
  Children {
    Text { Text: Rename, Typography_Role: label_large, Style { Foreground: on_surface } }
  }
}
```

`Timeout: 4000` closes it by itself that many milliseconds after it opens (the pointer over it holds the time off), and a `Handlers { On_Dismiss: ... }` runs whenever it closes itself or the user closes it.

Escape and a press outside close it, and write `false` to the Signal `Open` is bound to; with an `Open` that is not a Signal it stays closed until `Open`
goes false. Focus goes back to where it was. `Dismissible: false` turns both off.

`Modal: true` makes the layer a scrim (the `scrim` colour at 32%) over the whole window, blocking input to what is under it and keeping Tab inside; it
follows the window's size and centres its children unless the style places them (`Align_Content`). Put the dialog itself in a child, with its own size
and background. A press on the scrim closes a dismissible modal; a press on its content does not. Without an `Anchor` and not modal, the layer sits at its own `X` and `Y`.

## Focus

`focus('input')` in a handler gives the focus to the node named `input` in the same view (names are unique in a view, and a view never reaches into
the one it calls). `On_Press` with `Call { Action: focus, Args: [<| 'input' |>] }` on a container makes a click anywhere in it, padding included, land in the field inside it.

A `Focus_Group` makes a toolbar, a tab strip, a menu or a radio set behave as one control: Tab visits **one** of its items (the one that last had
the focus), the arrow keys of its axis move the focus to the next and the previous item (wrapping), `Home` and `End` go to the first and last, and typing
the start of an item's name jumps to it (the same letter again goes on to the next item that starts with it; a pause of a second starts a new search; typing in
a text field inside the group is the field's). Disabled items are skipped, and a group inside a group looks after its own items.

## Two-way properties

This is the one place that says what a view may write back; [Bindings](bindings.md) and [Components](component-fragments.md#letting-the-component-change-something-of-the-callers) point here.

A `model` property (a widget's `Text`, `Checked`, `Value`, `Selected`, `Open`; a view's `Model: true` param) given **one bare reference to a writable Signal** is
two-way: the user's edit is written back to it. The writable names are a `State` name, a `Model: true` param, and a Signal of the ViewModel.

```tdl
Switch {
  Selected: <| dark |>                 # toggling writes `dark`
}
```

Anything else is **one-way**: an expression (`<| not dark |>`), a literal, a Computed, an attribute of the ViewModel that is not a
Signal, a loop variable, a plain (not `Model`) param even when it holds a Signal. The widget shows the value, and the user's edit stays on screen, unwritten,
until the value next changes (a plain attribute never changes, so it stays). Write the change yourself in a handler (`On_Change { Set { Target: dark, Value: <| not dark |> } }`).

A property given one bare name that is none of the writable kinds (a Computed, a ViewModel attribute that is not a Signal, a plain param, a loop variable) looks two-way
and is not, so Tesserae says so in the log when the view is composed, with the file, line and column, once for that place:
`Main_View.tdl:7:14: Checkbox checked is given 'inverse', which is a Computed: the user's edit is not written back (one-way)`. It is a warning, not an error. Give the property a Signal or a
`State` name to make it two-way, or write an expression (`<| inverse and True |>`) to say that one-way is what you meant.

**What a handler may assign.** A `Set` writes a `State` name, a `Model: true` param of the view it is written in, or a Signal of the ViewModel.
It cannot write a plain param, a loop variable, a Computed, a ViewModel attribute that is not a Signal, `hovered`, `focused`, `pressed`, or a name nothing
has. This is found when the view loads, with the file, line and column, and the names that could be written (`'cuont' is not writable here ... did you mean 'count'`).

**A model param, by what the caller gives it.**

| The caller writes | The view gets | A write by the view |
| --- | --- | --- |
| a bare `State` name or ViewModel Signal | that Signal itself, through as many views as pass it on | reaches the caller |
| an expression (`<| n + 1 |>`) | a copy that follows the expression | stays in the copy until the expression next changes |
| a literal, or nothing | its own value | stays in the view |

A param that is not `Model: true` always follows what it is given and cannot be written.

**What `State` keeps.** A `State` Signal belongs to the node that declares it (and to each row of a `For`, by its key). When the view is edited and reloaded, a node that
keeps its name or position keeps the value the user left, **over an edited starting value**: change `State { N: 1 }` to `{ N: 100 }` and a running view still shows its `n`.
A renamed state, or a renamed or moved node, starts again from its starting value, and so does a row whose key is new. A ViewModel's Signals are not part of the view and are
untouched.

## Style

`Style` holds layout and paint: size and spacing (`Width Height Min_Width Max_Width Min_Height Max_Height Aspect_Ratio Padding Margin`),
flex and grid, alignment, position, `Background Border_Width Border_Color Corner_Radius Opacity Elevation`, effects (`Blur Backdrop_Blur
Blend_Mode Filter Cursor Pointer_Events Clip_Children`), and the widget's extras. Values may be expressions. A field that holds a map is a block of its own
(`Padding { Left: 12, Right: 12 }`). A size may be a sum (`calc(100% - 16)`), a node may be
placed by its edges (`Left`, `Top`, `Right`, `Bottom`, `Inset`) or against another node (`Anchor`, `Placement`, `Offset`): see [Layout](layout.md).

A **stylesheet** (`<Name>_Stylesheet.tdl`) is a root `Styles` block holding `Rule` blocks, so a look is written once and not on every node:

```tdl
Styles {
  Rule { Widget: Card, Style { Corner_Radius: 12 } }
  Rule { Widget: Card, Variant: outlined, Style { Border_Width: 1, Border_Color: outline } }
  Rule { Widget: Card, Part: headline, State: hovered, Style { Foreground: primary } }
}
```

A rule usually names a `Widget` (a built-in or a view; a rule of only `Classes`, a `Name` or a `Style` is allowed), and may add `Variant`, `Size`, `Shape` (properties the widget declares), `Classes`, `Name`, a
`Part` (a named node inside that widget's view; one the view does not have is an error that names the nearest, `Card has no part 'heading' (did you mean 'headline')`) and a `State` (`hovered focused focus_visible pressed disabled selected checked expanded error read_only visited`; the last seven read the
widget's own property). `Styles` holds `Rule` blocks only, in order, and a rule's `Style` is one block. The most specific rule wins: a `Name`, then the number of properties matched (with all the `Classes` counting as one more), then a `State`, then the
widget alone, and a later rule wins a tie. A widget's own shipped looks are the lowest layer and the app's stylesheet is above them. **A
node's inline `Style` beats every rule, for the fields it sets and no others.** A rule's value may be an expression over the widget's params.

## ViewModels

A view with a `Name` on its root node is bound to the ViewModel that serves that name; a view without one is a static visual.

```python
class DataViewModel(ViewModel):
    views = ["data_pie", "data_list"]          # the views it serves

    def __init__(self):
        super().__init__()
        self.rows = Signal([...])


app = App(root=".")
app.bind(DataViewModel)
app.open_view("DataPie")
app.open_view("DataList")
```

**One instance serves every view that names it**, wherever they are, so a pie chart and a list of the same rows are two views of one
Signal. `app.bind(DataViewModel)` makes it once, when the first view opens; `app.bind(instance)` uses yours; `app.bind(factory=DataViewModel)`
makes one per view instance. The ViewModel finds its open views in `self.views[name]`: `.node(name)`, `.state(var)`, `.show()`, `.hide()`, and
`self.show("data_phone", "data_list")` shows one in place of another. `on_attached(view)` and `on_detached(view)` are called as views open
and close.

`app.check()` compares every name, action and `Expects` entry of the open views with their ViewModels without a window. `Expects` is optional
data in a view's header: `Expects { Count: int, Rows: list, Add: handler }`.

## Tools

- `tesserae migrate-tdl [PATH] [--write] [--remove-source]` moves YAML views, stylesheets and themes to TDL: [Migrating](../migration.md#to-0601).
- A JSON schema of every widget's node, with its properties and style fields, ships in the package as `schema/tess-ui-widget-schema.json` (and one for a
  stylesheet of rules, `tess-ui-stylesheet-schema.json`). `tesserae schema --project` adds your own views to it: [Editor Support](editor-support.md).
