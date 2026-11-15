# Accordions

*Containment*

## In Material Design 3

Material Design 3 has no accordion of its own. Tesserae's is built in MD3's terms: a list row with a chevron
that turns when the section opens.

## In Tesserae

Two views Tesserae ships. `Accordion` is one section: a 56 pixel header button (the `Title` and a chevron that turns over in 200 milliseconds) and, while `Expanded`
(two-way), its content (the children). `AccordionGroup` makes several behave as one set with dividers between them.

A press, Enter or Space on the header toggles `Expanded`, and `On_Toggle` is called after it. A `Disabled` section is dimmed and does not toggle. An `AccordionGroup` takes
`Items`, each `{Value, Title, Text}` (the text is the section's content; for more than text, write the `Accordion` sections yourself); `Mode` is `single` (the default: opening one
closes the rest) or `multiple`, and `Open` is the value that is open (empty for none), or with `multiple` the list of values that are.

A screen reader hears a button that says whether it is expanded and what it controls; the content is hidden from it while closed and its parts are not built, so they
take no Tab stop. The up and down arrows move between the headers, and Home and End go to the first and last. Not built: the content's height easing open
(the engine cannot ease a height to `auto`).

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Accordion { ... }`. A file of the same name in your project replaces it.

### `Accordion`

One section of an accordion: a 56 pixel header button (the title, and a chevron that turns over when it opens) and, while `Expanded`, the content (the children). A press, Enter or Space toggles it; `Expanded` is two-way. A screen reader hears a button that says whether it is expanded and what it controls. `AccordionGroup` makes several of them behave as one set.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Title` | `str` |  | The header's text. |
| `Expanded` | `bool` | `false` | Whether the content shows. Two-way: give it a bare reference and the view writes it back. |
| `Disabled` | `bool` | `false` | Dimmed, and it does not toggle. |
| `On_Toggle` | `handler` |  | Called after the header has been pressed (a group uses it to close the others). |

Children go in the default slot.

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `header` (Container), `title` (Text), `filler` (Container), `chevron` (Icon), `content` (Container), `inner` (Container).

Its look is in [`Accordion_Stylesheet.tdl`](../stylesheets/accordions/accordion.md).

### `AccordionGroup`

Several accordion sections as one set, with a divider between them. `Items` is a list of {value, title, text} (the text is the section's content; for more than text, use `Accordion` sections yourself). `Mode: single` keeps one open (opening one closes the rest), `Multiple` lets any number be; `Open` is the value that is open, or the list of values with `Multiple`, and is two-way. The up and down arrows move between the headers, and Home and End go to the first and last.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Items` | `list` | `[]` | The sections, each {value, title, text}. |
| `Mode` | `single` or `multiple` | `single` | single: at most one open; multiple: any number. |
| `Open` | `any` |  | single: the value that is open (empty for none); multiple: the list of values that are open. Two-way: give it a bare reference and the view writes it back. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `section` (Container), `divider` (Divider), `panel` (Accordion), `text` (Text).

## Using it

```tdl
Container {
  Name: faq
  Style { Flex_Direction: vertical, Gap: 16, Width: 420, Height: 360 }
  Children {
    Accordion {
      Title: Details
      Expanded: <| showing |>
      Children {
        Text {
          Text: "More about it"
          Typography_Role: body_medium
          Style { Foreground: on_surface_variant }
        }
      }
    }
    AccordionGroup {
      Open: <| which |>
      Items {
        Item { Value: a, Title: Shipping, Text: "Two days." }
        Item { Value: b, Title: Returns, Text: "Thirty days." }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import accordion_header

details = accordion_header(app.window, "Details", expanded=False, width=320)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Accordion_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Accordion
    Part: title
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
