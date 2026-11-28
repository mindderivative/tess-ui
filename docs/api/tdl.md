# TDL Reference

Every key Tesserae's TDL files take, with the values it accepts and what it does. This page is written from the same schemas the editor tools use (`tesserae schema`), so it can't fall behind the code. For how the pieces fit, see the [guide](../guide/layout.md).

## The files

| File | What it is | Reference |
| --- | --- | --- |
| `<Name>_View.tdl` | A screen or a widget: one root block, with its children. | [The node](#the-node) |
| `<Name>_Stylesheet.tdl` | Style rules for a view or an app: a `Styles` block of `Rule`s. | [The stylesheet](#the-stylesheet) |
| `<Name>_Theme.tdl` | A theme: colours, type, shapes and style rules. | [The theme](#the-theme) |

## The file

A file starts with a metadata block, then holds one root block. `TDL` is the language version, `Name` the file's name and `Tesserae` the release series of the language it is written for. A `#` starts a comment. Every key is `Title_Case` (`Corner_Radius`, `On_Click`); a value that is a word is bare, other text is quoted, and an expression is a slot, `<| expr |>`.

```tdl
---
TDL: 0.2
Name: Counter
Tesserae: "0.6"
---
Container {
  Name: counter
  Style { Flex_Direction: vertical, Gap: 8, Padding: 16 }
  Children {
    Text { Text: <| 'Clicked ' + str(count) |> }
    If <| count > 0 |> {
      Button {
        Label: Reset
        Handlers { On_Click { Set { Target: count, Value: <| 0 |> } } }
      }
    }
  }
}
```

## The node

A view is one block headed by a widget, with its children inside it. A node is a block headed by its widget (`Button { ... }`); a scalar key is a property (`Label: Save`); a mapping is a block headed by its key (`Style { ... }`); the child nodes are in `Children { ... }`. Which blocks are nodes is told by where they are: a block directly in `Children`, `If` or `For` is a node, any other block in a node is a mapping.

| Key | Values | What it does |
| --- | --- | --- |
| `Name` | text | An optional handle, unique in the view: a letter or `_`, then letters, digits and `_`. A ViewModel, a rule's `Name` or `Part`, a test and a hot reload that keeps state find the node by it. |
| `Slot` | text | Which slot of the view being called this child goes into. |
| `State` | a block | Local state: a name and a starting value for each, as a Signal for this node and everything under it. |
| `Style` | a `Style` block | How the node looks and lays out its children: the [style fields](#the-style), and any extra the widget declares. |
| `Classes` | a list of names | Extra names a stylesheet rule's `Classes` can select. |
| `Handlers` | a `Handlers` block | What each event calls: see [Handlers](#handlers). |
| `A11y` | an `A11y` block | What assistive technology is told: see [Accessibility](#accessibility). |
| `Interaction` | `true` or `false`, or text | The hover, press and focus feedback of the node: `true`, `false`, a colour role, or an expression. |
| `Visible` | `true` or `false`, or text | `false` hides a built node: it takes no room and no pointer, but stays in the tree with its state. An expression is allowed. |
| `Window_Region` | `drag` or `none` | `drag`: a press here moves the window (a title bar); `none`: it does not. |
| `Route` | text | On a view call inside the window view: makes it a screen of the app; its route, such as `""`, `settings` or `notes/{id}`. |
| `Focus_Group` | `horizontal`, `vertical` or `both` | The focusable nodes under it share one Tab stop, and the arrow keys move among them. |
| `Tooltip` | text or a block | A tooltip: plain text, or a block with a title, text, delay and up to two actions. |
| `Params` | a `Params` block | On the root of a view file: the parameters the view takes, each with a `Type`, a `Default`, `Choices`, `Min`, `Max`, `Required`, `Model` and `Doc`. |
| `Expects` | a block | On the root of a view file: the names, actions and types the view expects of its ViewModel (checked by `app.check()`). |
| `Children` | a block of nodes | The child nodes, in order. |
| anything else | | A property of the widget: see [the widgets](#the-widgets). |

### Choosing and repeating

`If` and `For` wrap the one node they apply to; the node inside is built while the condition holds or once for each item:

```text
If <| loading |> {
  Circular_Progress { Name: spinner }
}
For item In <| items |> Key <| item['id'] |> {
  Chip { Label: <| item['name'] |> }
}
```

`For` takes one or several names (`For i, row In <| enumerate(rows) |> Key <| row['id'] |>`) and needs a `Key` (`Key <| None |>` for none). A node with both has the `For` outside and the `If` inside it. An `If` or `For` holds exactly one node.

## The widgets

A node's widget is a built-in one, one the app registered, or a view found by name (a file Tesserae ships, or `<Name>_View.tdl` of your own). Each takes its own properties, with a type, a default and the values it allows; the page of a component lists them.

| Widget | What it is |
| --- | --- |
| [`Accordion`](../components/accordions.md) | One section of an accordion: a 56 pixel header button (the title, and a chevron that turns over when it opens) and, while `Expanded`, the content (th… |
| [`AccordionGroup`](../components/accordions.md) | Several accordion sections as one set, with a divider between them. |
| [`Autocomplete`](../components/autocompletes.md) | The combo box (ux spec Autocomplete; the WAI-ARIA combobox with a listbox popup): an outlined text field with a popup list of options that narrows as… |
| [`Badge`](../components/badges.md) | The Material 3 badge: a 6 dp dot (no value) or a 16 dp pill holding a count or short text. |
| [`Button`](../components/buttons.md) | The Material 3 button: filled, tonal, elevated, outlined or text, in five sizes, with a leading and a trailing icon, a toggle form, a loading form an… |
| [`ButtonGroup`](../components/button-groups.md) | The Material 3 button group: buttons that behave as a set. |
| `Canvas` | A drawing surface: rects, circles and paths from data. |
| [`Card`](../components/cards.md) | The Material 3 card: a surface that holds content about one subject. |
| [`Carousel`](../components/carousel.md) | The Material 3 carousel: a row of rounded items that scrolls sideways and settles with an item lined up (the scroll view's `Snap`). |
| [`Checkbox`](../components/checkboxes.md) | A box that is on or off. |
| [`Chip`](../components/chips.md) | The Material 3 chip: assist (an action), filter (a toggle), input (a piece of what the user entered, with a close) or suggestion (a suggested reply o… |
| [`ChipGroup`](../components/chips.md) | A group of chips, wrapping onto new rows. |
| [`ChordRecorder`](../components/key-chord-fields.md) | The key-chord field's mind: it draws nothing. |
| [`CircularProgress`](../components/progress-indicators.md) | A progress ring. |
| [`ColourArea`](../components/colour-pickers.md) | A square of saturation (across) and value (up) for the colour's hue, with a handle: drag it, or move it with the arrow keys (Shift for a bigger step). |
| [`ColourField`](../components/colour-pickers.md) | A text field for the colour. |
| [`ColourPicker`](../components/colour-pickers.md) | The colour picker: a square of saturation and value, hue and alpha strips, a hex field, red, green, blue and alpha numbers, and a row of the theme's… |
| [`ColourPickerPanel`](../components/colour-pickers.md) | The inside of a colour picker, with no surface and no trigger: a square of saturation and value for the hue, a hue strip, an alpha strip, the hex tex… |
| [`ColourStrip`](../components/colour-pickers.md) | A strip with a handle that picks a colour's hue or its alpha: drag it, or use the arrow, Page Up, Page Down, Home and End keys. |
| [`ColourSwatches`](../components/colour-pickers.md) | A row of the theme's colour roles; pressing one sets `Value` to its colour. |
| [`Combobox`](../components/autocompletes.md) | The combo box's mind: it draws nothing. |
| `Container` | A box with an optional fill that lays out its children. |
| [`DatePicker`](../components/date-pickers.md) | The Material 3 modal date picker: a dialog with the chosen date at the top (and a button that swaps the grid for a typed field), the month with arrow… |
| [`DatePickerDay`](../components/date-pickers.md) | One day of a date picker (Material 3): a 48 pixel target holding a 40 pixel circle with the number in `body_large`. |
| [`Dialog`](../components/dialogs.md) | The Material 3 dialog, basic or (`Fullscreen: true`) full-screen: a modal panel over a scrim, with an optional icon, a headline, supporting text or y… |
| [`Divider`](../components/dividers.md) | The Material 3 divider: a thin line that separates content. |
| [`Dock`](../components/dock.md) | Panels docked around a centre. |
| [`DockPanel`](../components/dock-panel.md) | One panel of a Dock. |
| [`Fab`](../components/fabs.md) | The Material 3 floating action button, and its extended form: an icon in a prominent container, with a label beside it when `Label` is given. |
| [`FileBrowser`](../components/file-dialogs.md) | The file dialog's mind: it draws nothing. |
| [`FileDialog`](../components/file-dialogs.md) | The file dialog: a modal panel over a scrim for choosing a file to open (`Mode: open`, one or, with `Multiple`, several), a folder and a name to save… |
| [`FontBrowser`](../components/font-lists.md) | The font list's mind: it draws nothing. |
| [`FontList`](../components/font-lists.md) | The font list: a searchable list of the installed font families, each in its own face where the engine can draw it, either inline or (`Popup: true`)… |
| [`FontListPanel`](../components/font-lists.md) | The inside of a font list, with no surface and no button: a search field over a list of the installed font families, each shown in its own face when… |
| [`GraphNode`](../components/node-graph.md) | A node of a NodeGraph. |
| `Icon` | A glyph from the built-in set, or from SVG path data. |
| [`IconBrowser`](../components/icon-pickers.md) | The icon picker's mind: it draws nothing. |
| [`IconButton`](../components/icon-buttons.md) | The Material 3 icon button: standard, filled, tonal or outlined, in five sizes and three widths, round or square, with a toggle form that swaps its i… |
| [`IconPicker`](../components/icon-pickers.md) | The icon picker: a searchable grid of icons, either inline or (`Popup: true`) behind a button that shows the icon and its name and opens the grid in… |
| [`IconPickerPanel`](../components/icon-pickers.md) | The inside of an icon picker, with no surface and no trigger: a search field over a grid of icons (the built-in set, and the `.svg` and `.png` files… |
| [`Image`](../components/images.md) | A picture. |
| [`KeyChordField`](../components/key-chord-fields.md) | A field for a keyboard shortcut: the chord as text in an outlined text field (`Ctrl+Shift+F1`: the modifiers Ctrl, Alt, Shift and Meta in that order,… |
| [`LinearProgress`](../components/progress-indicators.md) | A progress bar. |
| [`Link`](../components/links.md) | Text that can be activated. |
| [`ListEditor`](../components/list-editors.md) | A list editor: the items of a list as rows, each with the widget of the item kind (`Item_Kind`: `Text` a text field, `number` a spin box bounded by `… |
| [`ListEditorRow`](../components/list-editors.md) | One row of a list editor: the widget of the item kind (a text field, a spin box, a switch, a button that opens a menu of choices, or a colour picker… |
| [`ListItem`](../components/lists.md) | The Material 3 list item: one, two or three lines of text with something before it and something after it. |
| [`ListModel`](../components/list-editors.md) | The list editor's mind: it draws nothing. |
| [`LoadingIndicator`](../components/progress-indicators.md) | An indeterminate wait indicator. |
| [`Menu`](../components/menus.md) | The Material 3 menu: a list of choices on a temporary surface next to the node it comes from (`Anchor`, the name of a node in the view that has the m… |
| [`MenuBar`](../components/menu-bars.md) | The desktop menu bar: a row of titles (File, Edit, View ...) across the top of a window, each opening a `Menu` of commands (ux spec Menu Bar; Materia… |
| [`MenuItem`](../components/menus.md) | One row of a menu (Material 3): 48 pixels tall, `label_large` text, an optional 24 pixel leading icon, trailing text such as a keyboard shortcut, and… |
| [`NavigationDrawer`](../components/navigation-drawer.md) | The Material 3 standard navigation drawer: a permanent column of destinations beside the content, 360 pixels wide (256 to 360), a `surface` column. |
| [`NavigationDrawerItem`](../components/navigation-drawer.md) | One destination of a navigation drawer (Material 3): a 56 pixel tall pill with a 24 pixel icon, a `label_large` label and, at the end, a badge (a cou… |
| [`NavigationDrawerModal`](../components/navigation-drawer.md) | The Material 3 modal navigation drawer: the same destinations, over the content on a scrim from the start edge, `surface_container_low` at level 1 wi… |
| [`NavigationDrawerPanel`](../components/navigation-drawer.md) | The inside of a navigation drawer, which `NavigationDrawer` (standard) and `NavigationDrawerModal` both put in a sheet: a header slot, the destinatio… |
| [`NavigationDrawerScreens`](../components/navigation-drawer.md) | A standard navigation drawer whose destinations are the app's screens: `Items` is a list of {screen, label, icon} and optionally {badge}, with {headi… |
| [`NavigationRail`](../components/navigation-rail.md) | The Material 3 navigation rail: a column of 3 to 7 destinations, 80 pixels wide (220 when `Expanded`, with the labels beside the icons). |
| [`NavigationRailItem`](../components/navigation-rail.md) | One destination of a navigation rail: an icon in a 56 by 32 pill with its label under it (or, in an expanded rail, a 56 high pill with the label besi… |
| [`NavigationRailScreen`](../components/navigation-rail.md) | One destination of a navigation rail that goes to a screen of the app (Tesserae's, not Material 3's): a `NavigationRailItem` that is selected while i… |
| [`NavigationRailScreens`](../components/navigation-rail.md) | A navigation rail whose destinations are the app's screens: `Items` is a list of {screen, label, icon} and optionally {badge}. |
| [`NodeGraph`](../components/node-graph.md) | A canvas of linked nodes you can pan, zoom and move. |
| `Overlay` | A layer over the window: a menu, a dialog, a popover. |
| [`Pagination`](../components/pagination.md) | Page navigation (not Material 3 itself, which has page indicators and a pager): previous and next, and between them the page numbers with an ellipsis… |
| [`PeriodSelector`](../components/time-pickers.md) | The AM / PM selector of a time picker (Material 3): two 40 pixel halves in a 52 pixel wide, 1 pixel `outline` frame with 8 pixel corners. |
| [`RadioButton`](../components/radio-buttons.md) | One choice of a group. |
| [`RangeSlider`](../components/sliders.md) | Picks two values, a least and a most, between `Min` and `Max` by dragging two handles. |
| `Rect` | A filled box that can hold children. |
| `ScrollView` | A scrolling viewport for its children. |
| [`SearchBar`](../components/search.md) | The Material 3 search bar: a 56 pixel `surface_container_high` pill with a leading icon (a search glass, or a menu button), the text being typed, and… |
| [`SearchView`](../components/search.md) | The Material 3 docked search view: the panel that opens under a search bar (`Anchor`, the bar's name in the calling view) and shows suggestions, hist… |
| [`SegmentedButton`](../components/segmented-buttons.md) | The Material 3 segmented button: two to five connected segments in one outlined pill. |
| [`SideSheet`](../components/side-sheets.md) | The Material 3 standard side sheet: supplementary content beside the main content, inline, so it pushes the content and takes room only while it is `… |
| [`SideSheetModal`](../components/side-sheets.md) | The Material 3 modal side sheet: the same header, scrolling content and actions as the standard one, over a scrim and on top of the content. |
| [`SideSheetPanel`](../components/side-sheets.md) | The inside of a side sheet (Material 3): a header with an optional back button, the title and a close button, a content area that scrolls, and a row… |
| [`Slider`](../components/sliders.md) | Picks a value between `Min` and `Max` by dragging. |
| `Slot` | Where a caller's children go in a view (a default slot, or a named one). |
| [`Snackbar`](../components/snackbars.md) | The Material 3 snackbar: a short message near the bottom of the window, over the content, that goes by itself. |
| [`SnackbarHost`](../components/snackbars.md) | Several snackbars, one after another (Material 3 shows one at a time). |
| [`SpinBox`](../components/spin-boxes.md) | A number with step buttons. |
| [`SpinBoxField`](../components/spin-boxes.md) | A spin box with a visible label above it and a line of supporting or error text under it, as a text field has them. |
| [`SplitButton`](../components/split-buttons.md) | The Material 3 split button: a main action and, 2 pixels beside it, a menu button whose chevron turns over while its menu is open. |
| [`Splitter`](../components/splitter.md) | Two panes with a draggable, keyboard-operable handle between them. |
| [`StatusBar`](../components/status-bar.md) | A status bar (a desktop convention, not Material 3): a thin strip at the bottom of a window with short items on its left, centre and right. |
| [`Svg`](../components/svg.md) | A vector picture. |
| [`Switch`](../components/switches.md) | A toggle. |
| [`Tabs`](../components/tabs.md) | The Material 3 tab bar: a row of tabs over a divider, an indicator under the selected one that slides to the next. |
| [`Text`](../components/text.md) | A run of text. |
| [`TextField`](../components/text-fields.md) | The Material 3 text field: a labelled box around a text input, with an optional leading icon, prefix, suffix, trailing icon, supporting text, charact… |
| [`TextInput`](../components/text-fields.md) | A bare text input (the part of a TextField that takes the typing). |
| [`TimeInput`](../components/time-input.md) | The keyboard form of a time picker (Material 3's "input mode"): an hour field, a colon, a minute field and, in 12-hour time, an AM / PM selector. |
| [`TimePicker`](../components/time-pickers.md) | The Material 3 modal time picker: a dialog with the time at the top (an hour and a minute you press to choose which the dial sets, and an AM / PM sel… |
| [`TimePickerDial`](../components/time-pickers.md) | The clock face of a time picker. |
| [`TitleBar`](../components/title-bar.md) | A custom title bar. |
| [`TokenButton`](../components/token-buttons.md) | The token button: a button that shows the theme token it holds (its ref, such as `$color.primary`, with a swatch when the token is a colour the view… |
| [`TokenList`](../components/token-buttons.md) | The token button's mind: it draws nothing. |
| [`Toolbar`](../components/toolbars.md) | The Material 3 toolbar: a row (or, floating, a column) of icon buttons with an optional action button at the end and an overflow menu. |
| [`TopAppBar`](../components/top-app-bar.md) | The Material 3 top app bar: a navigation icon, a title and up to three action icons across the top of a screen. |
| [`Tree`](../components/trees.md) | A tree (the WAI-ARIA tree pattern in Material 3's list terms): rows that open to show their children, one level inside the next (the rows are one fla… |
| [`TreeNode`](../components/trees.md) | One row of a tree: a leaf or a branch with a chevron that turns a quarter when it opens. |
| [`VideoPlayer`](../components/video.md) | A video player: a picture surface with the usual transport controls under it. |
| `VirtualList` | A scrolling list of equal rows that builds only the rows in view: its one child is a `For:`. |
| [`Window`](../components/window.md) | The root of an app window. |

## The style

A node's `Style` block is a mapping of these fields. The same fields go in a stylesheet's or theme's rules.

### Size and spacing

| Field | Values | What it does |
| --- | --- | --- |
| `Aspect_Ratio` | a number | Width over height: gives the missing side from the one set. |
| `Height` | a number or `auto` \| `fit-content` or a percentage such as `50%` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Margin` | a number or a block | Space outside it: one number, or `{Left, Right, Top, Bottom}`. |
| `Margin.Top` | a number | Space on the top side. |
| `Margin.Right` | a number | Space on the right side. |
| `Margin.Bottom` | a number | Space on the bottom side. |
| `Margin.Left` | a number | Space on the left side. |
| `Max_Height` | a number or `auto` or a percentage such as `50%` | The most height it can take. |
| `Max_Width` | a number or `auto` or a percentage such as `50%` | The most width it can take. |
| `Min_Height` | a number or `auto` or a percentage such as `50%` | The least height it can take. |
| `Min_Width` | a number or `auto` or a percentage such as `50%` | The least width it can take. |
| `Padding` | a number or a block | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| `Padding.Top` | a number | Space on the top side. |
| `Padding.Right` | a number | Space on the right side. |
| `Padding.Bottom` | a number | Space on the bottom side. |
| `Padding.Left` | a number | Space on the left side. |
| `Width` | a number or `auto` \| `fit-content` or a percentage such as `50%` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### Flex

| Field | Values | What it does |
| --- | --- | --- |
| `Flex` | `none` \| `expand_horizontal` \| `expand_vertical` \| `fill` | How it takes room in its parent: `none` (the default) is as big as its content and never squeezed, `expand_horizontal` and `expand_vertical` take the room left over in that direction, `fill` both. |
| `Flex_Direction` | `horizontal` \| `vertical` | How its children are laid out: `horizontal` (the default) or `vertical`. |
| `Flex_Wrap` | `no_wrap` \| `wrap` | `wrap` lets children flow onto more lines; `no_wrap` keeps one. |
| `Gap` | a number | Space between its children. |

### Alignment

| Field | Values | What it does |
| --- | --- | --- |
| `Align_Content` | `top_left` \| `top` \| `top_right` \| `left` \| `center` \| `right` \| `bottom_left` \| `bottom` \| `bottom_right` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |
| `Align_Self` | `top_left` \| `top` \| `top_right` \| `left` \| `center` \| `right` \| `bottom_left` \| `bottom` \| `bottom_right` | Its own place in its parent, over the parent's `Align_Content`. |
| `Align_Wrapped` | `start` \| `center` \| `end` \| `stretch` \| `between` \| `around` \| `evenly` | With `Flex_Wrap: wrap`: how the lines share the room left over. |
| `Spread` | `none` \| `between` \| `around` \| `evenly` | Spreads its children along the layout: `between` (the space goes between them), `around` or `evenly`. |

### Grid

| Field | Values | What it does |
| --- | --- | --- |
| `Align_Cells` | `top_left` \| `top` \| `top_right` \| `left` \| `center` \| `right` \| `bottom_left` \| `bottom` \| `bottom_right` | In a grid: where each item sits in its cell. |
| `Align_Tracks` | `start` \| `center` \| `end` \| `stretch` \| `between` \| `around` \| `evenly` | In a grid: how the tracks share the room left over. |
| `Column_Gap` | a number | Space between columns (defaults to `Gap`). |
| `Display` | `flex` \| `grid` | `Flex` (the default) or `grid`. |
| `Grid_Auto_Columns` | text | The size of columns the template doesn't name. |
| `Grid_Auto_Flow` | `row` \| `column` \| `row dense` \| `column dense` \| `dense` | How grid children fill the cells. |
| `Grid_Auto_Rows` | text | The size of rows the template doesn't name. |
| `Grid_Column` | text or an integer | Which grid column it takes: `2`, or `1 / 3`. |
| `Grid_Row` | text or an integer | Which grid row it takes: `2`, or `1 / 3`. |
| `Grid_Template_Columns` | text | The grid's columns, as in CSS: `1fr 2fr 100px`. |
| `Grid_Template_Rows` | text | The grid's rows, as in CSS. |
| `Row_Gap` | a number | Space between rows (defaults to `Gap`). |

### Position

| Field | Values | What it does |
| --- | --- | --- |
| `Anchor` | text | The name of another node in this view to sit against, or `parent` for the node it is inside. The node leaves the flow and follows the anchor with no lag; it stays in the tree, clipped and ordered as a child of its parent is. |
| `Bottom` | a number or `auto` or a percentage such as `50%` | How far an `absolute` node is from its parent's bottom edge; with `Top` it is stretched between the two. |
| `Inset` | a number or `auto` or a percentage such as `50%` | All four insets at once: an `absolute` node with `Inset: 8` fills its parent less 8 pixels each side. |
| `Left` | a number or `auto` or a percentage such as `50%` | How far an `absolute` node is from its parent's left edge; with `Right` it is stretched between the two. A node in the flow is moved by it. |
| `Offset` | a list | With `Anchor`: `[dx, dy]` pixels added to the point it sits on. |
| `Placement` | `below` \| `above` \| `start` \| `end` \| `top_start` \| `top_end` \| `bottom_start` \| `bottom_end` \| `center` | With `Anchor`: which side of the anchor (`below`, `above`, `start`, `end`) or which of its corners, or its centre, the node's centre sits on. |
| `Position` | `relative` \| `absolute` | `absolute` takes it out of the flow and places it at `X` and `Y`. |
| `Right` | a number or `auto` or a percentage such as `50%` | How far an `absolute` node is from its parent's right edge; with `Left` it is stretched between the two. |
| `Snap_Align` | `none` \| `start` \| `center` \| `end` | In a scroll view that has `snap`, this node is a place it settles on, with this edge of the node at the same edge of the view. |
| `Sticky` | a number | In a scroll view, it sticks this many pixels from the top edge as its siblings scroll past. |
| `Top` | a number or `auto` or a percentage such as `50%` | How far an `absolute` node is from its parent's top edge; with `Bottom` it is stretched between the two. A node in the flow is moved by it. |
| `X` | a number or `auto` or a percentage such as `50%` | Where an `absolute` node sits from the left; the same as `Left` (say one of them). |
| `Y` | a number or `auto` or a percentage such as `50%` | Where an `absolute` node sits from the top; the same as `Top` (say one of them). |
| `Z_Index` | an integer | Stacking order: higher is in front. |

### Docking

| Field | Values | What it does |
| --- | --- | --- |
| `Zone` | `left` \| `right` \| `top` \| `bottom` \| `center` | A DockPanel's zone in its Dock: where it docks. Only a DockPanel directly in a Dock has one; anywhere else it is an error. |

### Motion

| Field | Values | What it does |
| --- | --- | --- |
| `Rotation_Deg` | a number | Turns the node by this many degrees, clockwise, about its centre. |
| `Scale` | a number | Draws the node and what is in it at this multiple of its size (1 is unchanged), about its centre. |
| `Transition` | a block | Which style changes ease to their new value: a duration in milliseconds, or `{duration, easing, bounce}`. `all` covers every one that can. A node is where it says when first drawn; only a change eases. |
| `Transition.<Name>` | a number or a block | One for each of 21 names, such as `All`, `Background`, `Foreground`, `Border_Color`. |
| `Translate_X` | a number | Draws the node this many pixels to the right of where it is laid out. |
| `Translate_Y` | a number | Draws the node this many pixels lower than where it is laid out. |

### Paint and effects

| Field | Values | What it does |
| --- | --- | --- |
| `Backdrop_Blur` | a number | Blurs what is behind it, by this many pixels: with a translucent `Background`, a frosted surface. |
| `Background` | a color or a gradient | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Blend_Mode` | one of 16 names | How it is drawn over what is behind it, as CSS `mix-blend-mode`. |
| `Blur` | a number | Blurs the node and what it draws, by this many pixels. |
| `Border_Color` | a color or a gradient | The colour of its border: a colour or a gradient. |
| `Border_Width` | a number | The width of its border, in pixels. |
| `Clip_Children` | `true` or `false` | Whether children are cut off at its edge. |
| `Corner_Radius` | a number or `extra_large` \| `extra_small` \| `large` \| `medium` \| `none` \| `small` \| `full` or a list or a block | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Corner_Radius.Top_Left` | a number or `extra_large` \| `extra_small` \| `large` \| `medium` \| `none` \| `small` \| `full` | The radius of the top left corner. |
| `Corner_Radius.Top_Right` | a number or `extra_large` \| `extra_small` \| `large` \| `medium` \| `none` \| `small` \| `full` | The radius of the top right corner. |
| `Corner_Radius.Bottom_Right` | a number or `extra_large` \| `extra_small` \| `large` \| `medium` \| `none` \| `small` \| `full` | The radius of the bottom right corner. |
| `Corner_Radius.Bottom_Left` | a number or `extra_large` \| `extra_small` \| `large` \| `medium` \| `none` \| `small` \| `full` | The radius of the bottom left corner. |
| `Corner_Radius.Top` | a number or `extra_large` \| `extra_small` \| `large` \| `medium` \| `none` \| `small` \| `full` | The radius of both top corners. |
| `Corner_Radius.Right` | a number or `extra_large` \| `extra_small` \| `large` \| `medium` \| `none` \| `small` \| `full` | The radius of both right corners. |
| `Corner_Radius.Bottom` | a number or `extra_large` \| `extra_small` \| `large` \| `medium` \| `none` \| `small` \| `full` | The radius of both bottom corners. |
| `Corner_Radius.Left` | a number or `extra_large` \| `extra_small` \| `large` \| `medium` \| `none` \| `small` \| `full` | The radius of both left corners. |
| `Cursor` | one of 23 names or a block | The pointer over it: a name, or `{src: cursor.png, hotspot: [x, y]}` (a picture next to the view, at most 256 pixels a side; only in a node's own `Style:`). |
| `Cursor.Src` *(required)* | text | A PNG, JPEG, GIF or WebP picture next to the view. |
| `Cursor.Hotspot` | a list | `[X, Y]`: the pixel that is the pointer's place. |
| `Elevation` | a number or `level_0` \| `level_1` \| `level_2` \| `level_3` \| `level_4` \| `level_5` | A shadow level, 0 to 5. |
| `Filter` | a block | Colour filters over it and its children, as in CSS: `{grayscale: 1}`, `{saturate: 0.4, brightness: 0.9}` (`hue_rotate` is in degrees). |
| `Filter.Saturate` | a number | 1 is unchanged, 0 grey, above 1 more vivid. |
| `Filter.Brightness` | a number | 1 is unchanged, 0 black, above 1 brighter. |
| `Filter.Contrast` | a number | 1 is unchanged, 0 flat grey, above 1 harder. |
| `Filter.Grayscale` | a number | 0 is unchanged, 1 fully grey. |
| `Filter.Hue_Rotate` | a number | Turns the hues, in degrees. |
| `Filter.Invert` | a number | 0 is unchanged, 1 inverted. |
| `Filter.Sepia` | a number | 0 is unchanged, 1 fully sepia. |
| `Foreground` | a color or a gradient | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Opacity` | a number | From 0 (clear) to 1 (opaque). |
| `Overflow` | `hidden` \| `visible` | `Hidden` cuts what is inside to the node's own box, `Visible` lets it spill out: the same as `Clip_Children: true` and `false`, which it is another way to write (a node that says both must agree). It does not scroll: use a ScrollView for that. |
| `Pointer_Events` | `auto` \| `none` | `none` lets the pointer through the node itself: a click on it goes to whatever is under it, and it is not hovered or pressed. What is inside it keeps its own (a child with `auto` is still hit). `auto`, the default, is the usual. |

## Colors

Any field that takes a color takes a theme role (such as `surface` or `on_primary`), `#RGB`, `#RRGGBB`, `#RRGGBBAA`, `transparent`, a CSS colour name, or a CSS function such as `rgb(...)` or `oklch(...)`. End any of them with `@N%` to scale its alpha: `primary@12%`.

## Gradients

`Background`, `Foreground` and `Border_Color` take a gradient where they take a color: a CSS-like string (`linear-gradient(90deg, primary, tertiary)`, `radial-gradient(at 30% 30%, primary_container, surface)`, `conic-gradient(from 90deg, primary, secondary, primary)`; `to right` and the like name a direction; a stop may have a place, `primary 40%`). Stops are theme roles or colors. A control's color (a `Switch`, a `Slider`) takes a plain color only.

## Handlers

`Handlers` names what an event calls. An event is a property with a bare action name (`On_Click: save`), or a block of steps that run in order, each seeing the writes of the earlier ones: `Set { Target: name, Value: <| expr |> }` writes a name, `Call { Action: "name", Args: [<| expr |>] }` calls a ViewModel method or one of `window.minimize`, `window.maximize`, `window.restore`, `window.toggle_maximized`, `window.close`, `surface.dismiss`, `navigate.<Screen>`, `navigate.back`, `navigate.forward`.

```text
Handlers {
  On_Click {
    Set { Target: open, Value: <| not open |> }
    Call { Action: "on_toggle" }
  }
}
```

| Event | Values | What it does |
| --- | --- | --- |
| `On_Click` | an action name or a block of steps | Runs on the `click` event. |
| `On_Hover_Enter` | an action name or a block of steps | Runs on the `pointer_enter` event. |
| `On_Hover_Exit` | an action name or a block of steps | Runs on the `pointer_leave` event. |
| `On_Change` | an action name or a block of steps | Runs on the `change` event. |
| `On_Focus_Enter` | an action name or a block of steps | Runs on the `focus` event. |
| `On_Focus_Exit` | an action name or a block of steps | Runs on the `unfocus` event. |
| `On_Tap` | an action name or a block of steps | Runs on the `tap` event. |
| `On_Long_Press` | an action name or a block of steps | Runs on the `long_press` event. |
| `On_Pan` | an action name or a block of steps | Runs on the `pan` event. |
| `On_Pinch` | an action name or a block of steps | Runs on the `pinch` event. |
| `On_Touch_Start` | an action name or a block of steps | Runs on the `touch_start` event. |
| `On_Touch_Move` | an action name or a block of steps | Runs on the `touch_move` event. |
| `On_Touch_End` | an action name or a block of steps | Runs on the `touch_end` event. |
| `On_Touch_Cancel` | an action name or a block of steps | Runs on the `touch_cancel` event. |
| `On_File_Hover` | an action name or a block of steps | Runs on the `file_hover` event. |
| `On_File_Hover_Cancel` | an action name or a block of steps | Runs on the `file_hover_cancel` event. |
| `On_File_Drop` | an action name or a block of steps | Runs on the `file_drop` event. |
| `On_Link` | an action name or a block of steps | Runs on the `link` event. |

## Accessibility

`A11y` on any node.

| Key | Values | What it does |
| --- | --- | --- |
| `Label` | text | The name a screen reader says. |
| `Role` | one of 42 names | What kind of thing it is. |
| `Hidden` | `true` or `false` | Hide it from assistive technology. |
| `Live` | `assertive` \| `off` \| `polite` | How changes to it are announced. |
| `Level` | an integer | A heading's level. |
| `Expanded` | `true` or `false` or `null` or text | Open or closed, on something that opens and closes. |
| `Selected` | `true` or `false` or `null` or text | One of a set, chosen. |
| `Checked` | `true` or `false` or `null` or text | On or off. |
| `Value` | a number or `null` or text | A number the node holds. |
| `Value_Min` | a number or `null` or text | Its least. |
| `Value_Max` | a number or `null` or text | Its most. |
| `Value_Step` | a number or `null` or text | One step. |
| `Pressed` | `true` or `false` or `mixed` or `null` or text | A toggle button's state: true, false or `mixed`. |
| `Invalid` | `true` or `false` or `null` or text | The value is not acceptable. |
| `Description` | text or `null` | A longer description than the label. |
| `Describedby` | text or a list | The `Name:` of a node in this view that describes this one, or a list. |
| `Controls` | text or a list | The `Name:` of a node in this view that this one controls, or a list. |
| `Current` | `true` or `false` or `date` \| `location` \| `page` \| `step` \| `time` or `null` or text | The current item of a set: `page`, `step`, `location`, `date`, `time` or true. |
| `Value_Now` | a number or `null` or text | The value of a range. |
| `Value_Text` | text or `null` | How a range's value is said. |
| `Busy` | `true` or `false` or `null` or text | The node is updating. |

## The stylesheet

A stylesheet is a `Styles` block of `Rule` blocks, in order (a later rule wins a tie). A rule says which widgets it is for and the style it sets. See [Component stylesheets](../stylesheets/index.md).

```text
Styles {
  Rule {
    Widget: <text>
    Variant: <text>
    Size: <text>
    Shape: <text>
    Classes: <a list>
    Name: <text>
    Part: <text>
    State: <hovered | focused | focus_visible | pressed | disabled | ...>
    Style: <a Style block>
  }
}
```

| Key | Values | What it does |
| --- | --- | --- |
| `Widget` | text | The widget the rule is for: a built-in, or a view (`Button`). |
| `Variant` | text | Only widgets with this variant. |
| `Size` | text | Only widgets of this size. |
| `Shape` | text | Only widgets of this shape. |
| `Classes` | a list | Only nodes with all of these classes. |
| `Name` | text | Only the node with this name. |
| `Part` | text | A named node inside the widget's view (the widget's root when left out). |
| `State` | `hovered` \| `focused` \| `focus_visible` \| `pressed` \| `disabled` \| `selected` \| `checked` \| `expanded` \| `error` \| `read_only` \| `visited` | Only while the widget is in this state. |
| `Style` *(required)* | a `Style` block | The style fields the rule sets. |

## The theme

A theme is one `Theme` block. See [Themes](../themes/index.md).

```text
Theme {
  Seed: <a color>
  Dark: <true or false>
  Colors {
    <Name>: <a color>
  }
  Typography {
    <Name>: <a block>
  }
  Components: <a block>
  Styles {
    Item { Kind: ..., Classes: ..., Id: ..., Style: ... }
  }
}
```

| Key | Values | What it does |
| --- | --- | --- |
| `Seed` | a color | The colour the theme's palette is made from. |
| `Dark` | `true` or `false` | Whether it is the dark scheme. |
| `Colors` | a block | Colour roles to replace: a role name and a colour. |
| `Colors.<Name>` | a color | One for each of 49 names, such as `Background`, `Error`, `Error_Container`, `Inverse_On_Surface`. |
| `Typography` | a block | Changes to Material 3's type styles, by role. |
| `Typography.<Name>` | a block | One for each of 15 names, such as `Body_Large`, `Body_Medium`, `Body_Small`, `Display_Large`. |
| `Typography.<Name>.Font_Family` | text | A font family. |
| `Typography.<Name>.Font_Size` | a number | Pixels. |
| `Typography.<Name>.Font_Weight` | a number | 1 to 1000. |
| `Typography.<Name>.Line_Height` | a number | A multiple of the size. |
| `Typography.<Name>.Tracking` | a number | Extra space between letters, in pixels (Material 3's tracking: `tokens.MD3_TRACKING`). |
| `Components` | a block | Per-component shape and elevation. |
| `Styles` | a list | Style rules, in order. |
| `Styles[].Kind` | one of 34 names | Every node of this kind. |
| `Styles[].Classes` | a list | Nodes with all of these classes. |
| `Styles[].Id` | text | The node with this id. |
| `Styles[].Style` | a `Style` block | How the matching nodes look. |
