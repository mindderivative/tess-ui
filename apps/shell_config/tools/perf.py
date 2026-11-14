#!/usr/bin/env python3
"""Measures the window's two budgeted actions on a headless window over a copy of the representative configuration: selecting a block (Structure tree -> Form) and one committed form edit
(tree, form and text all updated). Prints the median and the worst of N runs, in milliseconds, with and without the frame that follows.

    PYTHONPATH=src:apps/shell_config/src python apps/shell_config/tools/perf.py [--runs 15]

It runs nothing that reaches the desktop (the toolkit's headless window draws into memory; DISPLAY and the session bus are removed first), reads only a temporary copy of the test configuration and the
recorded schema, and never starts a shell.
"""

from __future__ import annotations

import argparse
import os
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

for name in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
    os.environ.pop(name, None)

HERE = Path(__file__).resolve().parent
TESTS = HERE.parent / "tests"


def rows(nodes):
    for row in nodes:
        yield row
        yield from rows(row.get("children", []))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=15)
    args = parser.parse_args()
    from loguru import logger

    logger.remove()
    from tess_shell_config.app import build
    from tess_shell_config.schema import Schema
    from tess_shell_config.session import ConfigSession

    work = Path(tempfile.mkdtemp(prefix="shell-config-perf-"))
    try:
        shutil.copytree(TESTS / "fixtures" / "config", work / "cfg")
        schema = Schema.from_json((TESTS / "fixtures" / "schema.json").read_text(encoding="utf-8"))
        session = ConfigSession(work / "cfg", schema, None, state_dir=work / "state")
        built = build(session, reduced_motion=True)
        vm, window = built.viewmodel, built.window

        def frames(n: int = 4) -> None:
            for _ in range(n):
                window.advance(16)

        frames(8)
        vm.open_file("Shells/Main_Shell.tdl")
        frames()
        targets = {r["label"]: r["value"] for r in rows(vm.structure_nodes.get())}
        bar, other = targets["Bar  Top_Bar"], targets["Monitor  Primary"]
        select_set, select_all, edit_set, edit_all = [], [], [], []
        for i in range(args.runs):
            vm.structure_selected.set(other)
            frames()
            start = time.perf_counter()
            vm.structure_selected.set(bar)
            select_set.append((time.perf_counter() - start) * 1000)
            frames()
            select_all.append((time.perf_counter() - start) * 1000 - 0)
            start = time.perf_counter()
            vm.form_commit("k:Height|", {"text": str(30 + i % 2)})
            edit_set.append((time.perf_counter() - start) * 1000)
            frames()
            edit_all.append((time.perf_counter() - start) * 1000)
        items = len(vm.form_items.get())
        nodes = sum(1 for _ in built.view.handle.composition.walk())

        def line(name: str, values: list[float]) -> str:
            return f"{name:<46} median {statistics.median(values):7.1f} ms   worst {max(values):7.1f} ms   best {min(values):7.1f} ms"

        print(f"window nodes {nodes}, form items {items}, runs {args.runs}")
        print(line("select a block: the call", select_set))
        print(line("select a block: the call and 4 frames", select_all))
        print(line("one committed edit: the call", edit_set))
        print(line("one committed edit: the call and 4 frames", edit_all))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
