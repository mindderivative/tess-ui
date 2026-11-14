"""What the TDL tests share: a YAML view's text as TDL, through the real converter (`tess_ui.migrate_tdl`), and a way to compare two mappings.

The converter writes a pair-target loop with one variable (`i, it in enumerate(items)` -> `i_it`): `tess_ui.migrate_tdl.with_single_variable(data)` makes the YAML
mapping say the same, so the two can be compared.
"""

from __future__ import annotations

from typing import Any

from tess_ui.migrate_tdl import _handler_form, convert_view


def yaml_to_tdl(text: str, name: str) -> str:
    """The TDL text of the YAML view `text` (named `name`)."""
    return convert_view(text, name).text


def normal(data: Any) -> Any:
    """The mapping as plain data; handler texts as their statements written one way (the front end writes `a = b; c(d)`, and `x += 1` is `x = x + 1`)."""

    def walk(item: Any, key: str | None = None) -> Any:
        if isinstance(item, dict):
            if key == "handlers":
                return {k: _handler_form(v) if isinstance(v, str) else walk(v) for k, v in item.items()}
            return {k: walk(v, k) for k, v in item.items()}
        if isinstance(item, list):
            return [walk(v) for v in item]
        return item

    return walk(data)
