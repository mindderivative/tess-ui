# Key chord field

*Selection and input*

## In Material Design 3

Material Design 3 has no field for a keyboard shortcut. An app whose people set their own shortcuts needs one, and it is built from an outlined text field and a button that records.

## In Tesserae

`KeyChordField` is a view Tesserae ships (`KeyChordField_View.tdl`): an outlined text field that holds the chord as text, and a button beside it that records one. `ChordRecorder` is the
control that draws nothing and is its mind (`tess_ui.chord_controls`), and `tess_ui.key_chords` has the rules for the text.

The text is `Ctrl+Alt+Shift+Meta+Key`: the modifiers that are held, always in the order Ctrl, Alt, Shift, Meta, and then one key, last, the parts joined by `+`: `Ctrl+Shift+F1`, `Alt+Left`, `Meta+Space`. A named
key is in title case (`Escape`, `Enter`, `Backspace`, `Tab`, `Space`, `Delete`, `Insert`, `Home`, `End`, `PageUp`, `PageDown`, `Left`, `Right`, `Up`, `Down`, and `Plus`, `Minus`, `Comma`, `Period` for
the characters that cannot be written in a `+`-joined text); a function key is `F1` to `F24`; a letter is a capital; any other single character is itself. `Value` is two-way text; empty is no shortcut.

Recording. Press the button (or Tab to it and press Enter or Space) and it takes the next key press as the chord: it says "Press keys", and shows the modifiers held so far (`Press keys Ctrl+Shift+`) while the
person holds them. A modifier on its own (Shift, Control, Alt, Meta, a lock) never finishes the chord. A key that is not one finishes it: the chord is written to `Value`, `On_Change` is called, and the field
shows it. Escape on its own cancels and leaves the chord as it was; Backspace on its own clears it (`Value` is empty and `On_Change` is called); with a modifier they are chords like any other
(`Ctrl+Escape`). While recording, Enter and Space are chords too. A key that no chord can have (`print_screen`) is named under the field and the recording goes on. Leaving the button ends a recording. `Recording` is
two-way: set it true to start one from the app, and a finished or cancelled recording writes false.

Typing. The text in the field is read when Enter is pressed or the field is left, never per key. It is read in any case and in the usual names (`ctrl+shift+f1`, `Control + Return`, `super+pgup`, `Esc`,
`Del`, `arrow_left`): a chord is written back in the canonical form (`Ctrl+Enter`). Anything else is refused: `Value` stays as it was, the field is drawn in the error colours with the reason under it, and what was typed
stays to be mended. The media and hardware keys are written with the X key names without their `XF86` prefix (`AudioRaiseVolume`, `AudioLowerVolume`, `AudioMute`, `AudioMicMute`, `AudioPlay`, `AudioPause`, `AudioStop`, `AudioNext`, `AudioPrev`, `MonBrightnessUp`, `MonBrightnessDown`): recording one writes that name, and typing it with the prefix (`XF86AudioMute`) is read and written back without it. Typing nothing clears the shortcut. A value the app sets is shown as it is and never rewritten: `ctrl+shift+f1` stays so until the person commits it, and a value that is not a chord is shown in
the error colours and kept. The disabled field records and reads nothing.

A screen reader hears a group named by `Label`, the field with that label (and the error), and a button that says "Record label", or while recording "Recording label: press the keys, Escape cancels, Backspace clears",
and is `pressed` while it does. The field and the button are in the Tab order. The look is in `KeyChordField_Stylesheet.tdl`: write one in your project to change the button, which is `primary_container` while it records.
Not built: several chords for one action, a chord of two steps (`Ctrl+K Ctrl+S`), a list of the chords already taken, and key names for the keys the engine reports but this table does not know (a keypad, the media keys).

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `KeyChordField { ... }`. A file of the same name in your project replaces it.

### `KeyChordField`

A field for a keyboard shortcut: the chord as text in an outlined text field (`Ctrl+Shift+F1`: the modifiers Ctrl, Alt, Shift and Meta in that order, then one key, a named key in title case), and a button that records it. Press the button (or focus it and press Enter or Space) and the next key press is the chord (the `On_Click: n = n` below changes nothing: a box with no click handler cannot take the focus, and the pointer starts a recording on its press, so a key press that is also a click cannot start one again after it has ended it): Escape cancels, Backspace clears, and a modifier on its own (Shift, Control, Alt, Meta) only shows the modifiers held so far and does not finish it. A chord can also be typed: it is read when Enter is pressed or the field is left, in any case (`ctrl+shift+f1`, `Control+Return`), and written in the canonical form; text that is not a chord is refused, in the error colours, and `Value` is left as it was. `Value` is two-way text and is never rewritten for a value the app sets. `On_Change` is called after each change the person makes. What the parts do is in the ChordRecorder control (`tess_ui.chord_controls`), which this view drives by writing a numbered command to `cmd`.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Value` | `str` |  | The key chord, `Ctrl+Alt+Shift+Meta+Key`; empty is no shortcut. Two-way: give it a bare reference and the view writes it back. |
| `Recording` | `bool` | `false` | Whether the next key press is recorded as the chord. The button sets it; a finished or cancelled recording writes false. Two-way: give it a bare reference and the view writes it back. |
| `Label` | `str` | `Shortcut` | What a screen reader calls the field, and its label. |
| `Placeholder` | `str` | `"Not set"` | What the field says while it is empty and not being edited. |
| `Disabled` | `bool` | `false` | Dimmed and not editable. |
| `On_Change` | `handler` |  | Called after each change the person makes. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `recorder` (ChordRecorder), `field` (TextField), `record` (Container), `record_icon` (Icon), `record_text` (Text).

Its look is in [`KeyChordField_Stylesheet.tdl`](../stylesheets/key-chord-fields/key-chord-field.md).

### `ChordRecorder`

The key-chord field's mind: it draws nothing. It records a key press as a chord, reads a typed chord and writes it in the canonical form, and tells the view through the names it is bound to.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Value` | `str` |  | The key chord as text, `Ctrl+Alt+Shift+Meta+Key` (modifiers in that order, the key last, a named key in title case): `Ctrl+Shift+F1`. Empty is no shortcut. Recording and a committed typed text write it, in that form. Two-way. |
| `Draft` | `str` |  | The text of the field the chord is typed in: the control sets it to the chord after a recording or a commit, and the view's field writes it as the person types. Nothing is read from it until `Typed`. Two-way. |
| `Recording` | `bool` |  | Whether the next key press is recorded as the chord. The view sets it true to start; a finished or cancelled recording writes false. Two-way. |
| `Command` | `str` |  | What to do, written as text that starts with a number that is new each time (`7 key arrow_down`): `key arrow_left ctrl shift` (a key the button heard, then the modifiers held), `typed ctrl+shift+f1` (a text committed in the field), `record`, `stop`. |
| `Preview` | `str` |  | Output: written to the name it is bound to. While recording, the modifiers held so far, such as `Ctrl+Shift+`; otherwise empty. Two-way. |
| `Invalid` | `bool` |  | Output: written to the name it is bound to. The value is not a key chord, or the text typed was not one. Two-way. |
| `Message` | `str` |  | Output: written to the name it is bound to. Why `Invalid`, or why a key could not be recorded; empty when nothing is wrong. Two-way. |
| `Disabled` | `bool` |  |  |

## Using it

```tdl
Container {
  Name: shortcuts
  Style { Flex_Direction: vertical, Gap: 16, Width: 560, Height: 240, Padding: 16 }
  Children {
    KeyChordField {
      Value: <| reveal |>
      Label: "Reveal key"
      On_Change: reveal_changed
    }
    KeyChordField {
      Value: <| cycle |>
      Label: "Cycle surface"
    }
  }
}
```

## Using it in Python

```python
from tess_ui import key_chords

key_chords.normalise("control + return")                 # 'Ctrl+Enter'
key_chords.normalise("Ctrl+Shift")                       # None: no key
key_chords.from_event("arrow_left", alt=True)            # 'Alt+Left'
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# KeyChordField_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: KeyChordField
    Part: record
    Style { Corner_Radius: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Controls](../guide/controls.md)
- [Text Fields](../components/text-fields.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
