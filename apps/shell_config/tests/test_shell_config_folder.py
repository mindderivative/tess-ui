"""The configuration folder: where it is, and its files by type from each file's root block."""

import shutil
from pathlib import Path

from tess_shell_config.folder import FileType, default_config_dir, resolve_config_dir, scan

CONFIG = Path(__file__).parent / "fixtures" / "config"


def copy(tmp_path) -> Path:
    folder = tmp_path / "cfg"
    shutil.copytree(CONFIG, folder)
    return folder


def test_the_files_are_listed_by_the_type_of_their_root_block(tmp_path):
    files = scan(copy(tmp_path))
    by_type = {t: [f.rel for f in files if f.type is t] for t in FileType}
    assert by_type[FileType.SHELL] == ["Shells/Bom_Shell.tdl", "Shells/Broken_Shell.tdl", "Shells/Main_Shell.tdl", "Shells/No_Final_Newline_Shell.tdl", "Shells/Windows_Shell.tdl"]
    assert by_type[FileType.MODULE] == ["Modules/Hello/Hello_Module.tdl"]
    assert by_type[FileType.STYLE] == ["Styles/Hello_Style.tdl"]
    assert by_type[FileType.STYLESHEET] == ["Stylesheets/Main_Stylesheet.tdl"]
    assert by_type[FileType.THEME] == ["Themes/Dark_Theme.tdl"]
    assert by_type[FileType.SETTINGS] == ["settings.tdl"]
    assert by_type[FileType.OTHER] == []
    assert [f.type for f in files] == sorted((f.type for f in files), key=list(FileType).index), "listed in the Files area's order"


def test_the_type_comes_from_the_root_block_not_the_file_name(tmp_path):
    folder = copy(tmp_path)
    (folder / "Themes" / "Odd_Shell.tdl").write_text("---\nTDL: 0.1\nName: Odd\n---\nTheme { }\n")
    found = next(f for f in scan(folder) if f.rel == "Themes/Odd_Shell.tdl")
    assert found.type is FileType.THEME and found.name == "Odd" and found.parses


def test_a_file_that_does_not_parse_is_typed_by_its_name_and_counts_its_errors(tmp_path):
    files = {f.rel: f for f in scan(copy(tmp_path))}
    broken = files["Shells/Broken_Shell.tdl"]
    assert broken.type is FileType.SHELL and broken.errors >= 1 and not broken.parses
    (tmp_path / "cfg" / "Notes.tdl").write_text("not tdl at all")
    other = next(f for f in scan(tmp_path / "cfg") if f.rel == "Notes.tdl")
    assert other.type is FileType.OTHER and other.errors >= 1


def test_the_name_is_the_files_own_name_from_its_metadata(tmp_path):
    files = {f.rel: f for f in scan(copy(tmp_path))}
    assert files["Shells/Main_Shell.tdl"].name == "Main" and files["settings.tdl"].name == "Settings" and files["Modules/Hello/Hello_Module.tdl"].name == "Hello"


def test_generated_folders_and_hidden_files_are_not_listed(tmp_path):
    folder = copy(tmp_path)
    for name in ("schemas", "logs", "Icons", ".trash", ".git"):
        (folder / name).mkdir()
        (folder / name / "Ghost_Shell.tdl").write_text("---\nTDL: 0.1\nName: G\n---\nShell { }\n")
    (folder / "Shells" / ".Hidden_Shell.tdl").write_text("---\nTDL: 0.1\nName: G\n---\nShell { }\n")
    (folder / "Shells" / "notes.txt").write_text("x")
    assert not any("Ghost" in f.rel or "Hidden" in f.rel or f.rel.endswith(".txt") for f in scan(folder))


def test_a_missing_folder_is_an_empty_list(tmp_path):
    assert scan(tmp_path / "nowhere") == []


def test_scanning_reads_nothing_it_writes_nothing(tmp_path):
    folder = copy(tmp_path)
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.rglob("*") if p.is_file()}
    scan(folder)
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.rglob("*") if p.is_file()}


def test_the_folder_is_the_argument_then_the_status_then_the_default(tmp_path):
    env = {"XDG_CONFIG_HOME": str(tmp_path / "xdg"), "HOME": str(tmp_path / "home")}
    assert resolve_config_dir(str(tmp_path / "given"), "/from/status", env) == tmp_path / "given"
    assert resolve_config_dir(None, str(tmp_path / "status"), env) == tmp_path / "status"
    assert resolve_config_dir(None, None, env) == tmp_path / "xdg" / "tesserae-shell"
    assert default_config_dir({"HOME": "/h"}) == Path("/h/.config/tesserae-shell")
    assert default_config_dir({"XDG_CONFIG_HOME": "relative", "HOME": "/h"}) == Path("/h/.config/tesserae-shell")


def test_the_file_type_of_a_name():
    assert FileType.for_name("settings.tdl") is FileType.SETTINGS
    assert FileType.for_name("A_Shell.tdl") is FileType.SHELL and FileType.for_name("A_Stylesheet.tdl") is FileType.STYLESHEET
    assert FileType.for_name("A_Style.tdl") is FileType.STYLE and FileType.for_name("random.tdl") is FileType.OTHER
