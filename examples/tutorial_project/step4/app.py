from pathlib import Path

from tess_ui import App

HERE = Path(__file__).parent

app = App(
    width=420,
    height=520,
    title="Tasks",
    root=HERE,
    custom_theme="Brand",  # Themes/Brand_Theme.tdl: the colours, made from one seed
    stylesheet="Tasks",    # Styles/Tasks_Stylesheet.tdl: the look of every screen
)
app.bind(app.project.viewmodel("Main"))
app.open_view("Main")
app.show("Main")
app.run()
