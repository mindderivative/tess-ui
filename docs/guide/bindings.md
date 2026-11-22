# Binding Expressions

A `<| |>` expression keeps a widget property in step with your ViewModel:

```text
Text {
  Name: label
  Text: <| title |>
  Typography_Role: body_large
  Style { Foreground: on_surface }
}
```

The expression is worked out against the ViewModel when the view is
opened. Every `Signal` or `Computed` it reads becomes a dependency, and
a change to one works it out again and updates the property. An expression
that reads nothing that can change (literals, params with fixed values,
a loop variable over a fixed list) is worked out once.

An expression is a **Python subset** in TEL, the Tesserae Expression Language (`tess_el`),
a sandboxed evaluator: nothing in a view file can import, open a
file, reach `__class__` or run code the application did not expose. A mistake
TEL can see in the text (a method that is not on the lists below, a `**` with a literal exponent over 64, a function that does not exist) is an error when the view
loads, not when the expression runs. The limits are below.

A binding can drive text, sizes, colours and other numbers, `checked`
and `selected`, and `visible`: `false` takes a node out of the
layout and out of hit-testing, not just out of sight. There is a
conditional expression: `<| 'Restore' if app.maximized else 'Maximize' |>`. A value inside a
`Style` can be an expression too (`Style { Width: <| size * 2 |> }`). Text can mix words and
expressions: `Text: <| app.state.user + "'s tasks" |>`.

## What you can write

| | Examples |
|---|---|
| a name | a loop variable, a local `State`, a param, a ViewModel attribute (`count`, `title`), then `app` |
| an attribute of a value | `user.name`, `pt.x`; a dict reads by attribute too (`row.title`) |
| indexing and slices | `items[0]`, `table["key"]`, `items[n - 1]`, `name[:3]` |
| arithmetic | `a + b`, `a - b`, `-a`, `a * b`, `a / b`, `a // b`, `a % b`, `a ** 2` |
| comparison | `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `not in`, `is None` |
| logic and choice | `a and b`, `a or b`, `not a`, `x if cond else y` |
| literals and displays | `42`, `1.5`, `"text"`, `True`, `None`, `[1, 2]`, `{"a": 1}`, `f"{n} items"` |
| comprehensions | `[t.upper() for t in tags if t]` |
| built-in functions | `len min max abs round sum str int float bool sorted reversed range enumerate zip any all list dict tuple set isinstance` (`isinstance` takes `str int float bool list dict`), `format_number pluralize clamp`, and the date functions `date_add_days date_weekday days_in_month format_date current_date` (dates are `year-month-day` text), and `density_token app_density` (the density table of the UX spec), and `tree_rows` (the flat rows of a tree: what `Tree` shows) |
| methods of text | `lower upper title capitalize strip lstrip rstrip split splitlines join startswith endswith replace find count zfill isdigit isalpha center ljust rjust removeprefix removesuffix` |
| methods of lists, tuples, dicts | lists and tuples: `index`, `count` only (they are read-only: `items.append(x)` and `items.sort()` are errors, so assign a new list); dicts: `get keys values items` |

A **Signal or Computed reads as its value**: `count` and `count.get()` are
the same, and both keep the binding in step when it changes. This holds for a name (a ViewModel attribute, a state variable, a param) and for an attribute of an object
the application owns (`app.state.user`). A Signal inside a list or a dict (`rows[0]`, `d.k`) is not read in the middle of an expression: `rows[0] + 1` is an error, so
write `rows[0].get() + 1` (an expression that ends in one, `<| rows[0] |>`, reads it). On a Signal that holds a dict, `d.get()` is the dict's own `get` and needs a
key: write `d`.

A property the user edits (a text field's `text`, a `Checkbox`'s `checked`, a `Slider`'s `value`) is **two-way** when it is given
one bare reference to a Signal or a local `State` name: `Checked: <| done |>`. The user's edit is written back to `done`. Any
other expression (`<| not done |>`, `<| app.state.user |>`) is one-way: the widget shows its value, the user's edit stays on screen until the value
next changes, and a handler such as `on_change` does the writing. [Two-way properties](view-language.md#two-way-properties) has the whole rule: which
names a handler may write, what a model param does with each thing a caller gives it, and what `State` keeps when a view is reloaded.

Names and attributes starting with `_` do not exist for an expression (a name that is only `_` too).
A call is only a built-in function, a method of text, a list or a dict, or
`name.get()` on a Signal. An object the application owns can be read
(its public attributes), but it cannot be added, compared, formatted or
iterated by an expression, so its own methods never run from a view.

Every `A11y` field except `role` and `live` can be bound the same way (`label` must then be text, so write `<| n |> unread`, not `<| n |>`): see [Interaction & Accessibility](interaction.md#bound-fields).

### Video frames

An `Image` takes a `frame`: a value `(rgba, width, height)`,
`width * height * 4` bytes of RGBA and the frame's size. Each new value
is shown as it arrives, and `None` keeps the last one. Decoding the video
is the app's: a ViewModel sets a `Signal` of the latest frame, and the
view pushes it. The latest frame survives a re-theme and a reconcile.

```text
Image {
  Name: screen
  Fit: fill
  Frame: <| player_frame |>
  Style { Width: 640, Height: 360 }
}
```

`VideoPlayer { }` is that Image with transport controls under it: `frame`, `playing`, `position`, `duration` and the
rest are its properties ([Video](../components/video.md) has the list).

## Python's rules

Arithmetic and comparison are Python's: `1 == 1.0` is `True`, integers
do not wrap (an int over 4096 bits is an error), `7 / 2` is `3.5` and
`7 // 2` is `3`. Dividing by zero is an error. `and` and `or` return one
of their operands (`name or "Untitled"`), and `not` returns `True` or
`False`.

Every expression has limits, and a breach is an error that names it: 2000
characters of source (a text with `<| |>` parts counts as one, so a text over 2000 characters is an error even when each part is short), 1000 nodes, nesting 40 deep, 200 000 evaluation
steps, `range` up to 100 000, a result of up to 1 000 000 items,
`**` with an exponent up to 64, and text up to 1 MB (the whole text, when it has several slots). `%` formatting and
`str.format` are not available; use an f-string.

## Text with slots

Each slot of a text is an expression of its own: TEL is the language of the expressions and Tesserae splits the text, so `Battery <| level |>% (<| pluralize(n, 'cell') |>)` is
two expressions with the text between them. A value that is exactly one slot keeps the type of the expression (a number, a list, `None`); a slot with text around it, or
several slots, make text: each value is written as text (`None` is nothing, a number or a boolean its usual spelling) and the pieces are joined. An object of the application's cannot be put in text:
`<| settings |>` beside other text is `a Settings cannot be used in text` (code `value-not-plain`), so read an attribute of it. Each slot has its own evaluation budget (a text of three
slots may take three times the steps of one); the 2000 characters of source and the 1 MB of text count for the whole text. An error in a slot names that slot's own line and column.

## When a binding is wrong

A binding that doesn't parse, or fails to evaluate, is an error when the view loads. It names the file, line and column, and
gives a hint when there is one (an `ExprError` carries TEL's `code` too, such as `unknown-name`, `call-not-function`, `method-not-available`, `bad-call` or
`limit-range`, for tools and tests):

```
Counter_View.tdl:5:43: 'cont' is not defined (did you mean 'count')
```

A function name that does not exist is found when the view loads, with the line, not when the expression runs. In a property, an `If`,
a `For` or a stylesheet rule the only functions are the built-in ones (`clamp`, `min`, `max`, `len`, `format_number`, ...), so
`<| clmap(x, 0, 1) |>` is a load error naming `clmap` and offering the near names (`did you mean 'clamp'`). In a handler a call may also be
a built-in action (`copy`, `focus`, `after`, `navigate_to`, ...), a method of the ViewModel or a handler parameter; a name that is none of
these is a load error too (`bmup(2)` offers `bump`). An action is a step of its own (`Call`) or the whole value of a `Set` (`ok = copy(text)`); inside a bigger
expression (`ok = copy(text) and 1`) it is an error. Each step of a handler has its own evaluation budget. `app.check()` lists every name and action the open views use that their ViewModels
do not have, without a window.

## Who evaluates it

Tesserae does: `tess_ui.tel` puts TEL under the views, and `ComposedView` keeps the live nodes in step with what it reads.

A binding that changes a value sets it; one whose value hasn't changed
does nothing. Setting a value from a binding never counts as the user's
edit, so `on_change` runs only when the user changes the widget: typing in
a text field, or toggling a checkbox.
