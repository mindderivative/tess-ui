"""The code blocks of the docs pages, and the front ends that read them: shared by the tests of the docs.

The convention a page follows (the docs say it in `docs/guide/editor-support.md` and the tutorials show it):

- A complete view, stylesheet or theme is fenced ```tdl (or ```text with a `title="X.tdl"`). Its metadata block is optional: a block that does not start with
  `---` is read with `HEADER` put in front of it. The root word says which it is: `Styles` a stylesheet, `Theme` a theme, any other a view.
- A fragment (a few lines, a `Style` block, anything that is not a whole document) is fenced ```text and is not read.
- A block that shows the *old* form on purpose (a migration page) says so with `<!-- old-syntax: ... -->` on the line before its fence.
- A `--8<-- "file"` block includes a file of the repository: the file must be there (the example tests read it).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
#: The generated API and schema pages and the changelog quote what was, not what to write now.
LEFT_OUT = ("api/", "schema/", "changelog.md")
HEADER = "---\nTDL: 0.2\nName: Doc\n---\n"
FENCE = re.compile(r"^(<!-- old-syntax[^\n]*-->\n)?```([A-Za-z0-9_+-]*)([^\n]*)\n(.*?)^```", re.M | re.S)
INCLUDE = re.compile(r'^--8<-- "([^"]+)"\s*$')


@dataclass(frozen=True)
class Block:
    page: str  # the page, relative to docs/
    number: int  # the block's place on the page, from 1
    old: bool  # marked `<!-- old-syntax: ... -->`
    lang: str  # the fence's language word
    info: str  # the rest of the fence line
    text: str

    @property
    def id(self) -> str:
        return f"{self.page}#{self.number}"

    @property
    def is_tdl(self) -> bool:
        """A block meant as a whole TDL document: ```tdl, or ```text titled `X.tdl`."""
        return self.lang == "tdl" or (self.lang == "text" and re.search(r'title="[^"]*\.tdl"', self.info) is not None)

    @property
    def included(self) -> str | None:
        """The file a `--8<-- "path"` block puts in place, or None."""
        found = INCLUDE.match(self.text.strip())
        return found.group(1) if found else None


def pages(*, left_out: tuple[str, ...] = LEFT_OUT) -> Iterator[tuple[str, Path]]:
    for page in sorted(DOCS.rglob("*.md")):
        rel = page.relative_to(DOCS).as_posix()
        if not rel.startswith(left_out):
            yield rel, page


def blocks(*, left_out: tuple[str, ...] = LEFT_OUT) -> Iterator[Block]:
    for rel, page in pages(left_out=left_out):
        for number, (marker, lang, info, text) in enumerate(FENCE.findall(page.read_text(encoding="utf-8")), 1):
            yield Block(rel, number, bool(marker), lang, info.strip(), text)


def document(text: str) -> str:
    """A docs block as a whole file: with its metadata block put in front when it has none."""
    return text if text.lstrip().startswith("---") else HEADER + text


def kind_of(text: str) -> str | None:
    """`view`, `stylesheet` or `theme`, by the root word (nothing is parsed)."""
    from tess_ui.project import kind_of_tdl

    return kind_of_tdl(document(text))


def load(block_text: str, file_stem: str = "Doc") -> tuple[str, Any]:
    """Reads a docs block through the TDL front end of its kind and returns `(kind, what the loader makes of it)`: a `ViewDoc`, a `RuleSheet` or the theme
    dict. Raises what the loader raises (a `LoadError` for a mistake in the block)."""
    from tess_ui.shipped import ViewLibrary
    from tess_ui.spec import cascade
    from tess_ui.spec.nodes import parse_view
    from tess_ui.spec.rules import RuleSheet
    from tess_ui.spec.tdl_stylesheet import load_marked_tdl_stylesheet
    from tess_ui.spec.tdl_theme import load_theme_tdl
    from tess_ui.spec.widgets import WidgetDecl

    text = document(block_text)
    kind = kind_of(block_text) or "view"
    library = ViewLibrary()
    if kind == "stylesheet":
        file = f"{file_stem}_Stylesheet.tdl"
        return kind, RuleSheet.of(load_marked_tdl_stylesheet(text, file), file, text)
    if kind == "theme":
        file = f"{file_stem}_Theme.tdl"
        theme = load_theme_tdl(text, file)
        cascade.check_theme(theme, file)
        return kind, theme
    return kind, parse_view(text, f"{file_stem}_View.tdl", resolver=lambda name: library.decl(name) or WidgetDecl(name, view=True, container=True))
