#!/usr/bin/env python3
"""Puts `tesserae: <line>` on the first line of every YAML file Tesserae ships, and keeps it there (#292).

    python3 tools/stamp_language.py            # report the files that lack it or carry another line
    python3 tools/stamp_language.py --write    # prepend it, or change the value of one that is there

The files are the current language's: the shipped views and stylesheets, the default theme, the project templates and the examples, and the fenced
blocks in the docs that show a whole file (a ```yaml title="Main_View.yaml" block: a fence with a title naming a view, stylesheet or theme file, and not
marked `<!-- old-syntax -->`; the key goes on the block's first line, indented as the fence is). Not the older-syntax
fragments in `src/tesserae/spec/components/` and `tests/older_syntax/` (the missing key is what marks them as older), and not the tooling files
(`tools/*.yaml`, `mkdocs.yml`, the workflows). When a new line is started, change `LINE` in `src/tesserae/spec/marker.py` and run this with `--write`.
`tests/test_language_marker.py` runs `stamped()` over the same list.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tesserae.spec import marker  # noqa: E402

GLOBS = ("src/tesserae/views/*_View.yaml", "src/tesserae/views/*_Stylesheet.yaml", "src/tesserae/spec/default_theme.yaml",
         "src/tesserae/templates/*.yaml.tmpl", "examples/**/*.yaml")
FIRST = re.compile(r"tesserae[ \t]*:[^\r\n]*")
#: A docs fence that shows a whole file: ```yaml title="Views/Main_View.yaml"
FENCE = re.compile(r'^(?P<indent>[ \t]*)```ya?ml[ \t]+title="[^"]*_(?:View|Stylesheet|Theme)\.yaml"[ \t]*$')
DOCS = ("docs/**/*.md",)
DOCS_LEFT_OUT = ("docs/api/", "docs/schema/", "docs/changelog.md")


def files():
    return sorted({path for pattern in GLOBS for path in ROOT.glob(pattern) if path.is_file()})


def pages():
    """The docs pages that may hold a whole-file block."""
    return sorted(p for p in ROOT.glob(DOCS[0]) if p.is_file() and not p.relative_to(ROOT).as_posix().startswith(DOCS_LEFT_OUT))


def stamped_page(path):
    """The page's text with the key on the first line of each whole-file block that lacks it, or `None` when it already has them all."""
    lines = path.read_text(encoding="utf-8").split("\n")
    out, changed, i = [], False, 0
    while i < len(lines):
        out.append(lines[i])
        fence = FENCE.match(lines[i])
        if fence and not (i and lines[i - 1].lstrip().startswith("<!-- old-syntax")) and i + 1 < len(lines):
            first = lines[i + 1].strip()
            if not first.startswith(f"{marker.KEY}:"):
                out.append(f"{fence['indent']}{marker.KEY}: {marker.LINE}")
                changed = True
            elif first.split("#")[0].strip() != f"{marker.KEY}: {marker.LINE}":
                lines[i + 1] = f"{fence['indent']}{marker.KEY}: {marker.LINE}"
                changed = True
        i += 1
    return "\n".join(out) if changed else None


def stamped(path):
    """The text `path` should have, or `None` when it already has it."""
    text = path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in text[:4096] else "\n"
    line = f"{marker.KEY}: {marker.LINE}"
    found = FIRST.match(text)
    if found:
        return None if found[0].split("#")[0].strip() == line else line + text[found.end():]
    return line + newline + text


def main(argv):
    write = "--write" in argv
    todo = [(path, new) for path in files() if (new := stamped(path)) is not None]
    todo += [(path, new) for path in pages() if (new := stamped_page(path)) is not None]
    for path, new in todo:
        if write:
            path.write_text(new, encoding="utf-8") if path.suffix == ".md" else path.write_bytes(new.encode("utf-8"))
    print(f"{len(files())} files and {len(pages())} docs pages; {len(todo)} {'stamped' if write else 'lack tesserae: ' + marker.LINE + ' on the first line'}")
    return 0 if write or not todo else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
