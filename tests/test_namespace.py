"""#295: the Python package is `tess_ui`, and nothing that names the old package is left behind.

The import name `tesserae` clashes with an unrelated project of that name on PyPI. The command (`tesserae new`), the `tesserae:` first line of a YAML file and the
PyPI name `tesserae-ui` are not the import name and stay. These checks are the ones that would pass quietly if a rename missed something: a tool that finds no
files, a page with no modules, a baseline for files that are gone.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
#: `import tesserae`, `from tesserae.x import y`, or a dotted name such as `tesserae.spec.themes` (not `tesserae.exe`, the Windows command).
OLD_IMPORT = re.compile(r"\b(?:from|import) tesserae\b|\btesserae\.(?!exe\b)[A-Za-z_]")
#: The changelog and the migration page say what the old name was.
HISTORY = {DOCS / "changelog.md", DOCS / "migration.md"}
PAGES = sorted(p for p in DOCS.rglob("*.md") if p not in HISTORY) + [ROOT / "README.md", ROOT / "DEVELOPING.md"]


def test_the_package_is_tess_ui_and_no_tesserae_module_is_left():
    assert importlib.util.find_spec("tess_ui") is not None
    assert (ROOT / "src" / "tess_ui" / "__init__.py").is_file()
    assert not (ROOT / "src" / "tesserae").exists()


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_a_page_does_not_show_the_old_import_name(page):
    found = [f"{page.relative_to(ROOT)}:{n}: {line.strip()[:110]}"
             for n, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1) if OLD_IMPORT.search(line)]
    assert not found, "\n".join(found[:8])


def test_a_new_project_imports_tess_ui_in_every_python_file(tmp_path):
    from tess_ui import cli

    assert cli.main(["new", "hello", "--no-venv", "--dir", str(tmp_path)]) == 0
    assert cli.main(["add", "screen", "Settings", "--dir", str(tmp_path / "hello")]) == 0
    files = sorted((tmp_path / "hello").rglob("*.py"))
    assert len(files) >= 3  # app.py, a ViewModel, the new screen's ViewModel
    text = {f.name: f.read_text(encoding="utf-8") for f in files}
    assert "from tess_ui import" in text["app.py"]
    assert not {name for name, body in text.items() if OLD_IMPORT.search(body)}


def test_the_api_page_documents_the_tess_ui_modules_and_their_base_classes():
    """`tools/generate_api_docs.py` lists a class's base only when its module is in this package. A filter that still said `tesserae` leaves the page whole but drops
    every "extends" note, and the up-to-date test accepts that page, so the notes are asserted here."""
    page = (DOCS / "api" / "python.md").read_text(encoding="utf-8")
    assert "`tess_ui.app`:" in page and "`tess_ui.spec`:" in page
    assert page.count("\n## ") >= 10
    assert "-> None  # extends _Notifiable" in page and "Also has everything `_Notifiable` has." in page
    assert not OLD_IMPORT.search(page)


def test_the_mypy_baseline_names_files_that_exist():
    """A baseline whose keys were not moved with the package would turn every old error into a new one, or, if the tool were changed to skip them, hide it."""
    baseline = json.loads((ROOT / "tools" / "mypy_baseline.json").read_text(encoding="utf-8"))
    assert len(baseline) > 100
    gone = sorted({key.split("|", 1)[0] for key in baseline if not (ROOT / key.split("|", 1)[0]).is_file()})
    assert not gone, gone[:5]
    assert all(key.startswith("src/tess_ui/") for key in baseline)


def test_the_environment_variables_and_schema_files_follow_the_package():
    shipped = sorted(p.name for p in (ROOT / "src" / "tess_ui" / "schema").glob("*.json"))
    assert shipped and all(name.startswith("tess-ui-") for name in shipped), shipped
    assert sorted(p.name for p in (DOCS / "schema").glob("*.json")) == shipped
    names = set()
    for path in [*(ROOT / "src").rglob("*.py"), *(ROOT / "tools").glob("*.py")]:
        names |= set(re.findall(r"\bTESSERAE_[A-Z_]+", path.read_text(encoding="utf-8")))
    assert names <= {"TESSERAE_RECORD_TRE"}, sorted(names)  # that one moves with the engine rename (#296)
