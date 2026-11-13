"""tess_shell_config: the Configuration Application of Tesserae Shell, built on Tesserae UI (`tess_ui`) and `tess_dl`.

It edits the user's `.tdl` files in place and losslessly, builds its forms from the schema `tesserae-shell schema --json` exports, and validates with the shell's own `check`. It
talks to the shell only through the `tesserae-shell` command and does not import `tess_shell`.
"""

__version__ = "0.1.0.dev0"
