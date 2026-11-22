# Text fields

*Selection and input*

## In Material Design 3

A text field lets people enter and edit text. Material Design 3 has two kinds: a **filled** field, a tinted container with a line under
it, and an **outlined** one, a field with a border. The label is the field's name: it sits in the middle as a hint and moves up, smaller,
when the field has focus or text. Supporting text, a character counter, icons before and after, and an error state with its message
belong to the field.

## In Tesserae

`TextField` is a view Tesserae ships (`TextField_View.tdl`) with its look as rules (`TextField_Stylesheet.tdl`). It is built from
the `TextInput` widget, the bare input, and the nodes around it, so every part has a name a stylesheet can address.

`Text` is two-way: give it a bare reference and typing writes it. `Placeholder` shows while the field is empty and has focus (or has no label). `Supporting` is help under the
field, and `Error` is a message that gives the field the error look and replaces the supporting text. `Leading` and `Trailing` are icons (an error replaces the trailing one),
`Prefix` and `Suffix` are text around the typing, such as `$` and `USD`, and `Counter` shows how many characters are typed, of `Max_Length` when there is one (`0` is no limit).
`Multiline` makes Enter start a new line; `Obscured` makes a password (dots, with a button that shows the text); `Read_Only` lets the text be selected and copied but not
changed. `Mask` fits what is typed to a pattern (`###-####`: `#` a digit, `A` a letter, `*` either, `\` a literal). `Suggestions` is a list of texts: those that contain
what is typed show in a menu under the field (up to six), pressing one fills the field in, and Escape closes the menu.

Events: `on_key` for each key pressed in the field, `On_Edit` after each edit (once `Text` has been written), and `on_submit` for Enter in a field that is not
multiline.

**Typing effects.** `Typing_Effect: flash` tints the characters just typed with the primary colour and lets the tint fade (about a quarter of a second);
`fade_in` covers them in the background colour and lets that fade, so they seem to appear. Each is drawn exactly over what was inserted (a paste over
several lines gets a piece on each line), from the geometry the engine reports for the edit. The background `fade_in` uses is the first opaque fill going up from the
input, else the theme's `surface`. `Caret_Effect: glide` hides the engine's caret and draws one of Tesserae's own, which eases to each new place in about an eighth
of a second, stays solid while you type and blinks after a moment, and shows only while the field has the focus. When the app asks for reduced motion there is no
flash and no fade, and the caret jumps and does not blink. Neither takes the pointer or appears to a screen reader.

Five more properties tune them, each the field's own to set. `Typing_Duration` is how long a flash or a fade-in lasts, in milliseconds (260 for a flash and 180 for a fade-in
when left out; `0` leaves the effect out). `Flash_Color` is what a flash is tinted with: a theme role or a colour (`tertiary`, `#FF8800`, `primary@50%`), the primary colour
when left out. `Flash_Opacity` is how strong a flash starts, `0` to `1` (`0.24` when left out). `Glide_Duration` is how long the gliding caret takes to reach its new place
(`120` when left out; `0` makes it jump), and `Caret_Blink` is how long it is on, then off (`530` when left out; `0` keeps it solid). A number below `0`, or a strength outside
`0` to `1`, is an error that names the property and the line. The easing is not settable.

The parts a stylesheet can address are `box`, `label`, `input`, `prefix`, `suffix`, `leading_icon`, `trailing_icon`, `error_icon`,
`reveal_button`, `reveal_icon`, `indicator` (the line under a filled field), `supporting` and `counter`. The state of a rule is the state of
the whole field: `focused` is true while anything inside it has the focus, `hovered` while the pointer is over it, and `Error` and
`Disabled` read the field's own properties. The label glides between its two places (its position eases in 150 milliseconds; its size changes at once, as the
engine cannot ease a font size). A filled field has 4 pixel top corners and a square bottom, over its line. The input says it is described by the help line, so a
screen reader reads that too, and it is invalid while there is an error. Not built: moving into the suggestions with the arrow keys (press one with the pointer), the input method's
composition drawn by Tesserae (the engine draws the candidate window at the caret), and an exposed dropdown that is a select.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `TextField { ... }`. A file of the same name in your project replaces it.

### `TextField`

The Material 3 text field: a labelled box around a text input, with an optional leading icon, prefix, suffix, trailing icon, supporting text, character counter and an error state. `Variant: filled | outlined`. What it looks like is in TextField_Stylesheet.tdl; this file is its structure. `Text` is two-way: give it a bare reference (`Text: "<| query |>"`) and typing writes `Query`. At the `Compact` and `dense` density of the app, or with `Label_Placement: external`, the label is above the field, outside its 32 or 28 pixel container (ADR-0023); the floating label below is the default density's, and the Material size when no density is asked. The label is raised (small, at the top) while the field has focus or text, and sits in the middle as a hint otherwise; it glides between the two (`Transition:` on its position).

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Variant` | `filled` or `outlined` | `filled` | filled has a fill and a line under it; outlined has a border. |
| `Label` | `str` |  | The field's name; it also names the field for a screen reader. |
| `Text` | `str` |  | What the user has typed. Two-way: give it a bare reference and the view writes it back. |
| `Label_Placement` | `auto` or `external` | `auto` | Where the label sits: auto is the floating label in a 56 pixel container at the default density and the Material size, above the field at compact and dense; external puts it above the container at every density, and the container is 40, 32 or 28 pixels (ADR-0023). |
| `Placeholder` | `str` |  | Shown while the field is empty and focused (or has no label). |
| `Supporting` | `str` |  | Help under the field. |
| `Error` | `str` |  | An error message. When it is not empty the field shows the error look and the message replaces the supporting text. |
| `Leading` | `str` |  | A built-in icon name shown before the text. |
| `Trailing` | `str` |  | A built-in icon name shown after the text. |
| `Prefix` | `str` |  | Text before the typing, such as a currency sign. |
| `Suffix` | `str` |  | Text after the typing, such as a unit. |
| `Max_Length` | `int` | `0` | The most characters it takes; 0 is no limit. |
| `Typing_Effect` | `none` or `flash` or `fade_in` | `none` | What happens to the characters just typed: flash tints them for a moment; fade_in fades them in. Left out when the app asks for reduced motion. |
| `Typing_Duration` | `float`, 0 or more |  | How long a flash or a fade-in lasts, in milliseconds: 260 for a flash and 180 for a fade-in when left out; 0 leaves the effect out. |
| `Flash_Color` | `color` |  | What a flash is tinted with: a theme role or a colour; the primary colour when left out. |
| `Flash_Opacity` | `float`, 0 to 1 |  | How strong a flash starts, from 0 to 1: 0.24 when left out. |
| `Glide_Duration` | `float`, 0 or more |  | How long the gliding caret takes to reach its new place, in milliseconds: 120 when left out; 0 makes it jump. |
| `Caret_Blink` | `float`, 0 or more |  | The time the gliding caret is on and then off, in milliseconds: 530 when left out; 0 keeps it solid. |
| `Caret_Effect` | `none` or `glide` | `none` | glide draws the caret itself and eases it to each new place. It jumps, and does not blink, when the app asks for reduced motion. |
| `Mask` | `mask` |  | A pattern the typing is put in: # a digit, A a letter, * either, \ a literal; other characters come by themselves, as in (###) ###-####. |
| `Counter` | `bool` | `false` | Shows how many characters are typed (of max_length, when there is one). |
| `Multiline` | `bool` | `false` | Several lines; Enter makes a new one, so on_submit does not fire. |
| `Obscured` | `bool` | `false` | A password: dots instead of the text, with a button that shows it. |
| `Disabled` | `bool` | `false` | Dimmed, and takes no typing. |
| `Read_Only` | `bool` | `false` | The text can be selected and copied but not changed. |
| `On_Edit` | `handler` |  | Called after each edit the user makes, once `Text` has been written. |
| `Suggestions` | `list` | `[]` | Texts to offer while typing: those that contain what is typed show in a menu under the field, and pressing one fills it in. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `offers` (Menu), `external_label` (Text), `box` (Container), `leading_icon` (Icon), `body` (Container), `prefix` (Text), `input` (TextInput), `suffix` (Text), `error_icon` (Icon), `trailing_icon` (Icon), `reveal_button` (Rect), `reveal_icon` (Icon), `label_box` (Container), `label` (Text), `indicator` (Rect), `footer` (Container), `supporting` (Text), `counter` (Text).

Its look is in [`TextField_Stylesheet.tdl`](../stylesheets/text-fields/text-field.md).

### `TextInput`

A bare text input (the part of a TextField that takes the typing).

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Text` | `str` |  | What the user has typed. Two-way. |
| `Placeholder` | `str` |  | Shown, dimmed, while the field is empty. |
| `Multiline` | `bool` |  | Several lines; Enter makes a new one. |
| `Obscured` | `bool` |  | Shows dots instead of the text, and blocks copy and cut (a password). |
| `Max_Length` | `int` |  | The most characters it takes; 0 is no limit. |
| `Read_Only` | `bool` |  | The text can be selected and copied but not changed. |
| `Mask` | `mask` |  | A pattern the typed text is put in: # a digit, A a letter, * either, \ a literal; other characters come by themselves. |
| `Typing_Effect` | `none` or `flash` or `fade_in` | `none` | What happens to the characters just typed: `flash` tints them with the primary colour for a moment; `fade_in` fades them in out of the background. |
| `Typing_Duration` | `float`, 0 or more |  | How long a flash or a fade-in lasts, in milliseconds: 260 for a flash and 180 for a fade-in when left out; 0 leaves the effect out. |
| `Flash_Color` | `color` |  | What a flash is tinted with: a theme role or a colour (`primary@50%` works); the primary colour when left out. |
| `Flash_Opacity` | `float`, 0 to 1 |  | How strong a flash starts, from 0 to 1: 0.24 when left out. |
| `Caret_Effect` | `none` or `glide` | `none` | `glide` draws the caret itself and eases it to each new place; it blinks, solid while typing. The engine's caret is hidden meanwhile. |
| `Glide_Duration` | `float`, 0 or more |  | How long the caret takes to reach its new place, in milliseconds: 120 when left out; 0 makes it jump. |
| `Caret_Blink` | `float`, 0 or more |  | The time the gliding caret is on and then off, in milliseconds: 530 when left out; 0 keeps it solid. |
| `Typography_Role` | `str` |  |  |
| `Font_Family` | `str` |  |  |
| `Font_Size` | `float` |  |  |
| `Font_Weight` | `any` |  |  |
| `Disabled` | `bool` |  |  |

Its `Style` also takes `Foreground`.

## Using it

```tdl
Container {
  Name: signup
  Style { Flex_Direction: vertical, Width: 360, Height: 420, Gap: 16, Padding: 16 }
  Children {
    TextField {
      Name: email
      Label: Email
      Leading: search
      Text: <| email |>
      Error: <| email_error |>
      Supporting: "We never share it"
      Handlers {
        On_Submit: sign_up
      }
    }
    TextField {
      Name: password
      Variant: outlined
      Label: Password
      Obscured: true
      Text: <| password |>
    }
    TextField {
      Name: bio
      Label: "About you"
      Multiline: true
      Max_Length: 140
      Counter: true
      Text: <| bio |>
    }
  }
}
```

`TextInput` is the bare input, for when the field around it is your own: `text`, `Placeholder`, `Multiline`, `Obscured`, `Max_Length`,
`Read_Only`, `Disabled`, `Mask`, the typing and caret effects above (`Typing_Effect`, `Caret_Effect` and the five that tune them) and the font (`Typography_Role`,
`Font_Family`, `Font_Size`, `Font_Weight`); its colour is `Style.Foreground`. A `TextInput` needs a `Style.Background` and a `Typography_Role` (or `Font_Family`): without them the view does not build.

## Changing its look

Write rules for `TextField` in your app's stylesheet; they sit above the shipped ones, and a `Style:` on the node beats every rule for the
fields it sets.

```tdl
Styles {
  Rule {
    Widget: TextField
    Part: box
    Variant: filled
    Style { Background: surface_container_high, Corner_Radius: 12 }
  }
  Rule {
    Widget: TextField
    Part: indicator
    State: focused
    Style { Background: tertiary }
  }
}
```

A view named `TextField_View.tdl` in your project replaces the shipped field, and its shipped look with it.

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# TextField_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: TextField
    Part: box
    Variant: filled
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [View Language](../guide/view-language.md)
- [Bindings](../guide/bindings.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
