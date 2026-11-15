# Layout

A view lays out with flexbox: every node is a box, and a container
places its children in a row or a column. This page covers the layout
keys of a node's `Style` (all of them work in a stylesheet too) and the
`ScrollView` widget. Every style key is listed in the
[TDL reference](../api/tdl.md); the whole language is in
[The View Language](view-language.md).

## Rows and columns

`flex_direction` is `horizontal` (the default) or `vertical`. `gap` spaces
the children, `padding` insets them, and `margin` spaces a child from
its neighbours; both take a number or `{top:, right:, bottom:, left:}`.

```tdl
Container {
  Style { Flex_Direction: vertical, Gap: 12, Padding: 16, Width: 320 }
  Children {
    Text {
      Name: title
      Text: Settings
      Typography_Role: title_large
      Style { Foreground: on_surface }
    }
    Container {
      Name: row
      Style { Flex_Direction: horizontal, Gap: 8, Align_Content: left }
      Children {
        Rect {
          Name: swatch
          Style { Width: 24, Height: 24, Background: primary, Corner_Radius: 12 }
        }
        Text {
          Name: label
          Text: Primary
          Typography_Role: body_large
          Style { Foreground: on_surface }
        }
      }
    }
  }
}
```

## Placing children: `align_content`

`align_content` says where a node's children sit in it, as one of nine positions:

| | | |
| --- | --- | --- |
| `top_left` | `top` | `top_right` |
| `left` | `center` | `right` |
| `bottom_left` | `bottom` | `bottom_right` |

It means the same in a row or a column: `left` is the left edge, `bottom` the bottom, `center` the middle.
Not set, children start at the top left and a box with no `width` stretches across the layout, so a column of
`Rect`s fills the width. A `Text` is as wide as its text.

```tdl
Container {
  Style { Flex_Direction: vertical, Width: 240, Height: 120, Align_Content: center }  # a column, centred
  Children {
    Rect {
      Name: box
      Style { Width: 40, Height: 20, Background: primary }
    }
  }
}
```

`spread` shares out the room that is left along the layout: `between` puts it between the children,
`around` around each, `evenly` everywhere. `align_content` still places them across.

```tdl
Container {
  Style { Flex_Direction: horizontal, Width: 320, Spread: between, Align_Content: left }
  Children {
    Rect {
      Name: first
      Style { Width: 40, Height: 20, Background: primary }
    }
    Rect {
      Name: second
      Style { Width: 40, Height: 20, Background: primary }
    }
    Rect {
      Name: third
      Style { Width: 40, Height: 20, Background: primary }
    }
  }
}
```

A child puts itself somewhere else than its parent says with `align_self`, which takes the same nine
positions and acts across the layout.

## How a node takes room: `flex`

`flex` is a node's own sizing in its parent:

| Value | What it does |
| --- | --- |
| `none` (the default) | As big as its `width` and `height`, or its content, and never squeezed. |
| `expand_horizontal` | Takes the room left over, horizontally. |
| `expand_vertical` | Takes the room left over, vertically. |
| `fill` | Both. |

In a row, `expand_horizontal` takes what the other children leave (two of them split it), and
`expand_vertical` stretches the node to the row's height; in a column it is the other way round. An
explicit `width` is the size it starts from, and `expand_*` overrides it across the layout.

## Sizes

`width` and `height` take pixels, `"auto"` (the default: its content's
size, or stretched), `"fit-content"` (its content's size along the line of the layout: across it a box is still stretched unless its parent sets
`align_content` or it sets `align_self`), a percentage of
the parent (`"50%"`), or a sum of those such as `"calc(100% - 16)"`
([below](#a-size-that-is-the-parent-minus-something)). A size is never
negative. `min_width`, `max_width`, `min_height` and `max_height` bound it
with a number, `"auto"` or a percentage, and `aspect_ratio` (width over
height) gives the missing side from the one that's set: a side the layout stretches is not computed, so set `align_content` on the parent or
`align_self` on the node (or use `flex_wrap`). A `Text` with no `width` is measured to its text; `Width: auto` stretches it like any box. A size that tess_re
would refuse (`40px`, `10vw`, `stretch`, `100%-16`) is an error at the line
that writes it, saying what to write.

### Text in a box

A `Text` or `Link` with no `width` or `height` is measured to fit its
text (a `Text` needs a `typography_role` or a `font_family`). Its `text_align` property places the text inside its width: `start` (the default), `center` or `end`.
A `Text` that is `center` or `end` aligned and has no `width` of its own fills its parent's width, so
there is room to align in; its text's width is the least it takes. Give it a `width` to choose another.

```tdl
Text {
  Text: Settings
  Typography_Role: title_large
  Text_Align: center
  Style { Width: 240, Foreground: on_surface }
}
```

A `TextField` has no `text_align`: what is typed starts at the left.

#### One line, or an ellipsis

A line too long for its box breaks onto the next (`Wrap: word`, the default). `Wrap: none` keeps one line
(and the text is then always drawn from the start: `text_align` has nothing to align within),
and `Overflow: ellipsis` ends a line that doesn't fit with an ellipsis instead of cutting it off
(`Overflow: clip`, the default). Together they make a single-line label that truncates:

```tdl
Text {
  Text: "A very long note title"
  Typography_Role: body_large
  Wrap: none
  Overflow: ellipsis
  Style { Width: 160, Foreground: on_surface }
}
```

Give the text a width (a number, or `Flex: expand_horizontal` in a row with `Min_Width: 0`) for the ellipsis to have
something to truncate to. A `TextField` has neither property.

The labels of the built-in [components](../components/index.md) are single lines that end in an
ellipsis when they don't fit. `Max_Lines: 2` stops a long text at two lines (with `Overflow: ellipsis` the second ends in an
ellipsis), and a Text with a width and no height is as tall as the lines it wraps to; `Letter_Spacing: 0.5` adds space between the letters, in pixels.

## Sharing a row

`Flex: expand_horizontal` shares the space left over (it on two children splits it evenly); the other
children keep their sizes.

```tdl
Container {
  Style { Flex_Direction: horizontal, Width: 400, Height: 48, Gap: 8 }
  Children {
    Rect {
      Name: sidebar
      Style { Width: 120, Background: surface_container }
    }
    Rect {
      Name: main
      Style { Flex: expand_horizontal, Max_Width: 400, Background: surface_container_high }
    }
  }
}
```

## Wrapping

`Flex_Wrap: wrap` starts a new row (or column) when the children don't
fit. With a fixed `width` it gives a gallery of
equal tiles. `align_wrapped` (`start`, `center`, `end`, `stretch`, `between`, `around`, `evenly`) says how
the lines share the room left across the layout.

```tdl
Container {
  Style { Flex_Direction: horizontal, Flex_Wrap: wrap, Gap: 8, Width: 340 }
  Children {
    Rect {
      Name: tile
      Style { Width: 100, Aspect_Ratio: 1, Background: secondary_container, Corner_Radius: 12 }
    }
    Rect {
      Name: tile2
      Style { Width: 100, Aspect_Ratio: 1, Background: secondary_container, Corner_Radius: 12 }
    }
    Rect {
      Name: tile3
      Style { Width: 100, Aspect_Ratio: 1, Background: secondary_container, Corner_Radius: 12 }
    }
    Rect {
      Name: tile4
      Style { Width: 100, Aspect_Ratio: 1, Background: secondary_container, Corner_Radius: 12 }
    }
  }
}
```

Rows of a wrapped layout don't line up their columns with each other,
and a tile can't span two columns: for that, use a grid.

## Grids

`Display: grid` lays a container's children out in rows and columns.
`grid_template_columns` and `grid_template_rows` list the tracks: pixels, `auto` (its content), `fr` (a share of what's
left), percentages, `minmax(min, max)` and `repeat(n, ...)`, as a string
(`"120 1fr"`) or a list (`[120, "1fr"]`). Children fill the cells in
order.

```tdl
Container {
  Style { Display: grid, Grid_Template_Columns: "1fr 1fr", Row_Gap: 12, Column_Gap: 16, Width: 360, Padding: 16 }
  State { Name: "", Email: "" }
  Children {
    TextField {
      Name: name
      Label: Name
      Text: <| name |>
    }
    TextField {
      Name: email
      Label: Email
      Text: <| email |>
    }
  }
}
```

- `grid_auto_rows` and `grid_auto_columns` size the tracks the templates
  don't list, and `grid_auto_flow` fills by `row` (the default) or
  `column`, `dense` to fill holes.
- A child is placed with `grid_column` and `grid_row`: a line number
  (`2`, or `-2` counting from the end), a span (`"span 2"`), or a range
  (`"1 / 3"`).
- `row_gap` and `column_gap` space the tracks; `gap` sets both, and
  either one wins over it.
- `align_cells` (on the grid) places the items in their cells, as one of the nine positions, and
  `align_self` (on a child) places one; `align_tracks` (`start`, `center`, `end`, `stretch`, `between`,
  `around`, `evenly`) places the tracks in a grid bigger than they are. A grid uses these instead of
  `align_content` and `spread`.

A dashboard of tiles, one spanning two columns:

```tdl
Container {
  Style { Display: grid, Grid_Template_Columns: "repeat(3, 1fr)", Grid_Auto_Rows: 96, Gap: 8, Width: 360 }
  Children {
    Rect {
      Name: wide
      Style { Grid_Column: "span 2", Background: primary_container, Corner_Radius: 12 }
    }
    Rect {
      Name: one
      Style { Background: secondary_container, Corner_Radius: 12 }
    }
    Rect {
      Name: two
      Style { Background: secondary_container, Corner_Radius: 12 }
    }
    Rect {
      Name: three
      Style { Grid_Column: "2 / 4", Background: tertiary_container, Corner_Radius: 12 }
    }
  }
}
```

A `ScrollView` can be a grid too: its `display` and track keys lay out
its children, and a `grid_column` on it places the scroll view in its
own parent.

## A size that is the parent minus something

A size may be a sum: `Width: "calc(100% - 16)"`, or the same without the wrapper, `"100% - 16"`. The terms are numbers, percentages and pixels
written `16px`, joined by `+` and `-` with a space each side; there is no `*`, `/` or `min()`, and a unit other than pixels (`vw`, `em`) is an error. A sum works
for `width` and `height`; the limits (`min_width`...) take a number, `auto` or a percentage. A sum may be an expression (`Width: <| gutter |>`
working out to `"100% - 24"`). In the flow you often do not need one, because the layout does the sum and follows the parent when it changes:

```tdl
Container {
  Style { Flex_Direction: vertical, Width: 300, Gap: 8 }
  Children {
    # the full width less an 8 pixel gutter each side (100% - 16)
    Rect {
      Name: bar
      Style { Height: 20, Flex: expand_horizontal, Margin { Left: 8, Right: 8 }, Background: primary }
    }

    # two columns with a 16 pixel gutter (50% - 8 each)
    Container {
      Name: columns
      Style { Gap: 16, Height: 20 }
      Children {
        Container {
          Name: left
          Style { Flex: fill, Background: secondary }
        }
        Container {
          Name: right
          Style { Flex: fill, Background: tertiary }
        }
      }
    }

    # what is left of a row after a fixed part (100% - 80)
    Container {
      Name: split
      Style { Height: 20 }
      Children {
        Rect {
          Name: icon
          Style { Width: 80, Height: 20, Background: error }
        }
        Container {
          Name: rest
          Style { Flex: fill, Background: outline }
        }
      }
    }
  }
}
```

An **absolutely positioned** node stretched between two edges of its parent takes insets instead (below).

## Placing a node against another node

Three style fields place a node against another node, wherever it is written, and keep it there as the target moves (tess_re lays it out after the target, so
there is no lag):

```tdl
Container {
  Style { Width: 300, Height: 200, Padding: 40 }
  Children {
    Rect {
      Name: target
      Style { Width: 60, Height: 40, Background: primary }
    }
    Rect {
      Style { Anchor: target, Placement: top_end, Offset: [6, -6], Width: 12, Height: 12, Background: error }
    }
  }
}
```

| Field | What it says |
| --- | --- |
| `anchor` | The `name` of the node to sit against, or `parent` for the node it is written inside. The nearest node of that name wins: in a `For` row it is the row's own node, then the view's, then the view that called this one. |
| `placement` | `below` (the default), `above`, `start`, `end`, or a corner: `top_start`, `top_end`, `bottom_start`, `bottom_end`, or `center`. A corner puts the node's *centre* on that corner of the target (and `center` on the target's centre); `offset` moves it from there. |
| `offset` | `[dx, dy]` in pixels, added to the placement. |

The node stays in the tree, so a parent's `clip_children` cuts it and its `z_index` orders it among its siblings, unlike a layer. It takes itself out of the
flow (it is absolute by itself). `anchor`, `placement` and `offset` may come from a stylesheet rule or an expression. A missing anchor name is an error at the
node, with the nearest name; a bad `placement` or `offset` is found at load. Take the fields out and the node is back in the flow. `placement` or `offset` with no `anchor` (written on the node or given by a rule) is an error that names the node, since they would do nothing; an `Anchor:` that is an expression and works out to nothing is not that, and leaves the node in the flow.

If the anchor goes (an `If`), or is hidden with `Visible:` (its own, or that of anything it is inside), the node is hidden with it and comes back when the anchor does,
unless its own `Visible:` says no. A control with a `Label:` is anchored as the row that holds the box and its label. `Transition` does not ease a placement.

An `Overlay` is the same thing as a layer: drawn above the whole window, not cut by a parent's `clip_children`, its own Tab scope. It takes the corners and `offset`
too, and `Flip: false` keeps it where it is put instead of moving it to the other side when it does not fit (the default, `true`, suits a menu; a marker wants
`false`). See [Overlays](overlays.md).

## Placing a node exactly

`Position: absolute` takes a node out of the flow, and `x`/`y` place it
in its parent, in pixels or percentages. The insets `left`, `top`, `right` and `bottom` say how far it is from each edge of its parent, and `inset` says all four
at once: `Left: 8, Right: 16` stretches a node across its parent less 8 and 16 pixels, and `Inset: 4` fills the parent less 4 each side. An inset is a number
(it may be negative), a percentage or `auto`. `x` is the same as `left` and `y` as `top`; giving both, or `x` with `inset`, in one `Style` is an
error, since one would not be heard. A rule's `inset` gives way to an edge the node (or a more specific rule) says itself. On a node in the flow an inset moves it from its place. An inset
does not ease: `Transition` takes `x` and `y` for a position. A control with a `Label:` (a `Checkbox`, `RadioButton` or `Switch`) is placed as the row that holds the box and its label, so an inset or a margin
moves both. `z_index` (an integer)
draws it above or below its siblings, and a container with
`Clip_Children: true` cuts its children to its own box. `Overflow: hidden`
is another way to write that (and `Overflow: visible` is `Clip_Children: false`); a node that gives both must
agree. It does not scroll: a `ScrollView` does. `Pointer_Events: none` lets the pointer through a node
(see [Gradients & Effects](effects.md#the-pointer)).

```tdl
Container {
  Style { Width: 200, Height: 120, Clip_Children: true, Background: surface_container }
  Children {
    Rect {
      Name: badge
      Style { Position: absolute, X: 176, Y: 8, Width: 16, Height: 16, Corner_Radius: 8, Background: error, Z_Index: 1 }
    }
    Rect {
      Name: strip
      Style { Position: absolute, Left: 8, Right: 8, Bottom: 8, Height: 4, Background: primary }
    }
  }
}
```

## Scrolling

`ScrollView { }` scrolls its children vertically when they're taller
than it. Its `Style` sizes, places and paints the scroll view;
`flex_direction` (vertical by default), `gap`, `padding`, alignment and
wrapping lay out its children inside it.

```tdl
Container {
  Style { Width: 320, Height: 400 }
  Children {
    ScrollView {
      Name: list
      Style { Width: 320, Height: 200, Gap: 4, Padding: 8, Background: surface }
      Children {
        Rect {
          Name: first
          Style { Height: 56, Background: surface_container, Corner_Radius: 12 }
        }
        Rect {
          Name: second
          Style { Height: 56, Background: surface_container, Corner_Radius: 12 }
        }
        Rect {
          Name: third
          Style { Height: 56, Background: surface_container, Corner_Radius: 12 }
        }
        Rect {
          Name: fourth
          Style { Height: 56, Background: surface_container, Corner_Radius: 12 }
        }
      }
    }
  }
}
```

- The wheel scrolls it. The keys do too, when it or a node inside it has
  focus: the arrows by a line, Page Up and Page Down by its height, Home
  and End to the ends. A node that handles keys itself keeps them (a
  text field keeps its arrows, but not Page Up and Page Down). Keys held
  with Ctrl, Alt or Meta are shortcuts and don't scroll; Shift still
  does. The scroll view is a Tab stop, so it can be scrolled with nothing
  inside it focusable.
- A `ScrollView` inside another passes on what it can't use, as in a
  browser: a wheel or a scroll key over an inner one that's already at
  that end, or whose content fits, scrolls the one outside it. One that can move takes the whole wheel
  or key.
- A child that takes focus is scrolled into view, just as far as needed,
  and so is one assistive technology asks to see (`scroll_into_view`).
- `Scroll_Offset: <| pos |>`, one bare reference to a Signal or a `State`
  name, is two-way: setting it scrolls, and scrolling writes back where the
  user scrolled, to save and restore a position. An offset past the end is
  held at the end at once, and that is what's written back (on the next frame, when the Signal was the one that set it). `at_top`,
  `at_end` and `scroll_direction` report where it is, the same way (see
  [Scrolling](view-language.md#scrolling)).
- Its scrollbar is the theme's `outline`.
- It scrolls vertically, or sideways with `Orientation: horizontal` (its children then sit in a row, and `scroll_direction` is `right` or `left`).
- `Snap: start` (or `center`, `end`) makes it settle, when scrolling stops, on the nearest child whose style has a matching `snap_align`.

For a list built from data, put a node with a `For` inside a `ScrollView`
(the rows are all built). For thousands of equal rows, use a `VirtualList`,
which builds only the rows in view: [Long lists](view-language.md#long-lists).

## Hiding a node

`Visible: false` on any node takes it out of the layout (it takes no room and no pointer) while it stays in
the tree. `Visible: true` puts it back at once. An expression is allowed: `Visible: <| expanded |>`.
