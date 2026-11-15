from pathlib import Path

from tess_ui import App

from Tasks_ViewModel import TasksViewModel

HERE = Path(__file__).parent

app = App(
    width=420,
    height=520,
    title="Tasks",
    root=HERE,
    search=["."],
    custom_theme=HERE / "Brand_Theme.tdl",   # the colours: made from one seed
    stylesheet=HERE / "Tasks_Stylesheet.tdl",  # the look of every screen
)
app.bind(TasksViewModel)
app.open_view("Tasks")
app.show("Tasks")
app.run()
