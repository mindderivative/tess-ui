# Search

*Navigation*

## In Material Design 3

A search bar is a rounded field that starts a search; the search view is the full-size surface that shows
suggestions and results once it is focused.

## In Tesserae

Two views Tesserae ships. `SearchBar` is a 56 pixel `surface_container_high` pill at level 3 with a leading icon, the text, and trailing parts. `SearchView`
is the docked panel that opens under it with the suggestions, history and results.

`Query` is what has been typed. `Active` says the search is under way: pressing the bar or typing in it sets it, and the back arrow clears it. The bar has a `Placeholder`, a
`Leading_Icon` (a search glass; `menu` makes it a menu button that runs `On_Leading`), an optional `Trailing_Icon` (a microphone, say, that runs `On_Trailing` and shows
while the field is empty) and an optional avatar (`Avatar_Text`); Enter calls `On_Search`. The `Results` of a `SearchView` are `{Value, Label}` rows, optionally with `Supporting` and
`Icon`; the row pressed goes to `Chosen`, `Open` says whether the view shows, and `Anchor` names the bar it sits under. `Frosted: true` makes the bar and the view translucent
and blurred.

A clear button shows once there is text. While active the leading icon is a back arrow. Bind the bar's `Active` and the view's `Open` to the same name, and the view's `Results` to
something that follows `Query`. The view says how many results there are, politely, and `Empty` text when a query finds none. Escape and a press outside close it. Not built:
the full-screen search view for small windows, and a keyboard shortcut that focuses the bar.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `SearchBar { ... }`. A file of the same name in your project replaces it.

### `SearchBar`

The Material 3 search bar: a 56 pixel `surface_container_high` pill with a leading icon (a search glass, or a menu button), the text being typed, and trailing parts: a clear button once there is a `Query`, an optional `Trailing_Icon` (a microphone) and an optional avatar (`Avatar_Text`). Pressing it, or typing in it, makes it `Active` (two-way; a `SearchView` shows while it is), and while it is active the leading icon becomes a back arrow that deactivates it. Enter calls `On_Search`. `Query` is two-way.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Frosted` | `bool` | `false` | A translucent surface that blurs what is behind it (72% of its colour, a 20 pixel backdrop blur). |
| `Query` | `str` |  | What has been typed. Two-way: give it a bare reference and the view writes it back. |
| `Placeholder` | `str` | `Search` | Shown while the field is empty. |
| `Active` | `bool` | `false` | Whether the search is under way (the view shows); focusing the bar sets it, the back arrow clears it. Two-way: give it a bare reference and the view writes it back. |
| `Leading_Icon` | `str` | `magnify` | The icon at the start while it is not active (menu, for a menu button). |
| `On_Leading` | `handler` |  | What the leading icon does when it is not a search glass (open a drawer). |
| `Trailing_Icon` | `str` |  | An icon at the end, such as a microphone. |
| `On_Trailing` | `handler` |  | What the trailing icon does. |
| `Trailing_Icons` | `list` | `[]` | More icons at the end, each an icon name (a Python widget wires each one itself). They show while nothing is typed, after `Trailing_Icon`. |
| `Avatar_Text` | `str` |  | Letters in a circle at the end. |
| `On_Search` | `handler` |  | Called when Enter is pressed. |
| `Disabled` | `bool` | `false` | Dimmed and not editable; the clear button is not shown. |
| `Clear_Label` | `str` | `Clear` | The name of the clear button for assistive technology. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `back` (Container), `back_icon` (Icon), `leading` (Container), `leading_glyph` (Icon), `input` (TextInput), `clear` (Container), `clear_icon` (Icon), `trailing` (Container), `trailing_glyph` (Icon), `trailing_item` (Container), `trailing_item_glyph` (Icon), `avatar` (Container), `avatar_text` (Text).

Its look is in [`SearchBar_Stylesheet.tdl`](../stylesheets/search/search-bar.md).

### `SearchView`

The Material 3 docked search view: the panel that opens under a search bar (`Anchor`, the bar's name in the calling view) and shows suggestions, history and results as list rows. `Results` is a list of {value, label} and optionally {supporting, icon}; pressing a row sets `Chosen` to its `Value` and closes the view. With a `Query` and no results the `Empty` text shows. Escape and a press outside close it (writing false to `Open`). The number of results is announced politely. Bind `Open` to the bar's `Active`.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Frosted` | `bool` | `false` | A translucent surface that blurs what is behind it (72% of its colour, a 20 pixel backdrop blur). |
| `Open` | `bool` | `false` | Whether the view is showing; Escape and a press outside write false. Two-way: give it a bare reference and the view writes it back. |
| `Anchor` | `str` |  | The name of the search bar in the calling view. |
| `Results` | `list` | `[]` | The rows: {value, label} and optionally {supporting, icon}. |
| `Query` | `str` |  | What is typed, so the empty state can say there is nothing. |
| `Chosen` | `any` |  | The value of the row pressed. Two-way: give it a bare reference and the view writes it back. |
| `Empty` | `str` | `"No results"` | Shown when there is a query and no rows. |
| `Width` | `float` | `360` | How wide the view is (the bar's width). |
| `Max_Height` | `float` | `400` | The rows scroll beyond this. |
| `History_Icon` | `str` | `history` | The icon of a row that gives none. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `panel` (Container), `count` (Text), `none` (Text), `rows` (ScrollView), `row` (ListItem).

Its look is in [`SearchView_Stylesheet.tdl`](../stylesheets/search/search-view.md).

## Using it

```tdl
Container {
  Name: notes
  Style { Flex_Direction: vertical, Width: 420, Height: 420, Padding: 16 }
  Children {
    SearchBar {
      Name: bar
      Query: <| q |>
      Active: <| searching |>
      Placeholder: "Search notes"
      Style { Width: 360 }
    }
    SearchView {
      Anchor: bar
      Open: <| searching |>
      Query: <| q |>
      Results: <| matches |>
      Chosen: <| picked |>
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import search_bar

search = search_bar(app.window, "Search notes", 360)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# SearchBar_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: SearchBar
    Part: back_icon
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Effects](../guide/effects.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
