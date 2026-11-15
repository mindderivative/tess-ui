"""#208: nested routes, guards and lazy screens in a window view."""

import pytest

from tess_ui import App
from tess_ui.spec.nodes import LoadError

SHELL = """---
TDL: 0.2
Name: shell
---
Window {
  Name: shell
  Title: App
  State { Signed: false }
  Style { Width: 600, Height: 300 }
  Children {
    Rect {
      Name: sign_in
      Style { Width: 40, Height: 20, Background: primary }
      Handlers {
        On_Click { Set { Target: signed, Value: <| True |> } }
      }
    }
    Home {
      Name: home
      Route: ""
    }
    Settings {
      Name: settings
      Route: settings
    }
    Admin {
      Name: admin
      Route { Path: admin, Guard: signed, Redirect: "" }
    }
    Reports {
      Name: reports
      Route { Path: reports, Lazy: true }
    }
  }
}
"""
LEAF = """---
TDL: 0.2
Name: NNN
---
Container {
  Name: NNN
  State { Count: 0 }
  Style { Width: 100, Height: 50 }
  Children {
    Rect {
      Name: bump
      Style { Width: 20, Height: 20, Background: primary }
      Handlers {
        On_Click { Set { Target: count, Value: <| count + 1 |> } }
      }
    }
    Text {
      Name: t
      Text: NNN
      Typography_Role: body_medium
      Style { Foreground: on_surface }
    }
  }
}
"""
SETTINGS = """---
TDL: 0.2
Name: settings
---
Container {
  Name: settings
  Style { Width: 300, Height: 100 }
  Children {
    Text {
      Name: t
      Text: settings
      Typography_Role: body_medium
      Style { Foreground: on_surface }
    }
    Profile {
      Name: profile
      Route: profile
    }
    Account {
      Name: account
      Route: "/account"
    }
  }
}
"""
ADMIN = """---
TDL: 0.2
Name: admin
---
Container {
  Name: admin
  Style { Width: 300, Height: 100 }
  Children {
    Text {
      Name: t
      Text: admin
      Typography_Role: body_medium
      Style { Foreground: on_surface }
    }
    Users {
      Name: users
      Route: users
    }
  }
}
"""


@pytest.fixture
def shell(tmp_path):
    (tmp_path / "Views").mkdir()
    files = {"Shell": SHELL, "Settings": SETTINGS, "Admin": ADMIN}
    for n in ("Home", "Profile", "Account", "Users", "Reports"):
        files[n] = LEAF.replace("NNN", n.lower())
    for n, text in files.items():
        (tmp_path / "Views" / f"{n}_View.tdl").write_text(text)
    app = App(root=tmp_path)
    view = app.open_view("Shell")
    app.window.advance(16)
    app.navigate_to("")
    app.window.advance(16)
    return app, view


def shown(view, *names):
    out = {}
    for name in names:
        path = {"home": "root.home", "settings": "root.settings", "profile": "root.settings.profile", "account": "root.settings.account",
                "admin": "root.admin", "users": "root.admin.users", "reports": "root.reports"}[name]
        out[name] = bool(view.node(path).get("visible")) if path in view._built.nodes else None
    return out


def test_a_nested_route_is_under_its_parents_path(shell):
    app, view = shell
    app.navigate_to("settings/profile")
    assert app.current == "Profile" and app.location == "settings/profile"
    app.navigate_to("settings")
    assert app.current == "Settings"


def test_an_absolute_nested_route_starts_from_the_root(shell):
    app, view = shell
    app.navigate_to("account")
    assert app.current == "Account"
    with pytest.raises(KeyError):
        app.navigate_to("settings/account")


def test_a_parent_shows_while_its_child_is_current_and_its_siblings_do_not(shell):
    app, view = shell
    app.navigate_to("settings/profile")
    app.window.advance(16)
    assert shown(view, "home", "settings", "profile", "account") == {"home": False, "settings": True, "profile": True, "account": False}
    app.navigate_to("account")
    app.window.advance(16)
    assert shown(view, "settings", "profile", "account") == {"settings": True, "profile": False, "account": True}
    app.navigate_to("")
    app.window.advance(16)
    assert shown(view, "home", "settings", "profile", "account") == {"home": True, "settings": False, "profile": False, "account": False}


def test_back_and_forward_walk_nested_screens(shell):
    app, view = shell
    app.navigate_to("settings/profile")
    app.navigate_to("account")
    app.back()
    assert app.current == "Profile"
    app.back()
    assert app.current == "Home"
    app.forward()
    assert app.current == "Profile"


def test_a_guard_that_fails_keeps_the_app_where_it_is_or_goes_to_the_redirect(shell):
    app, view = shell
    app.navigate_to("settings")
    app.navigate_to("admin")  # not signed in: sent to ""
    assert app.current == "Home" and app.can_go_back.get() is True


def test_a_guard_follows_the_state_it_reads(shell):
    app, view = shell
    app.navigate_to("admin")
    assert app.current == "Home"
    app.window.simulate("click", node=view.node("root.sign_in"))
    app.window.advance(16)
    app.navigate_to("admin")
    assert app.current == "Admin"


def test_a_parents_guard_covers_its_children(shell):
    app, view = shell
    app.navigate_to("admin/users")
    assert app.current == "Home"
    app.window.simulate("click", node=view.node("root.sign_in"))
    app.window.advance(16)
    app.navigate_to("admin/users")
    assert app.current == "Users"


def test_back_into_a_screen_a_guard_now_refuses_does_not_go(shell):
    app, view = shell
    app.window.simulate("click", node=view.node("root.sign_in"))
    app.window.advance(16)
    app.navigate_to("admin")
    app.navigate_to("settings")
    assert app.current == "Settings"
    app._frame.view.handle  # the shell is the frame
    app.guard("Admin", lambda params: False)
    assert app.back() is False and app.current == "Settings"


def test_a_python_guard_can_send_the_app_elsewhere(shell):
    app, view = shell
    app.guard("Settings", lambda params: "")
    app.navigate_to("reports")
    app.navigate_to("settings")
    assert app.current == "Home"


def test_guards_that_send_each_other_round_are_named(shell):
    app, view = shell
    app.guard("Settings", lambda params: "reports")
    app.guard("Reports", lambda params: "settings")
    with pytest.raises(ValueError, match="in a circle"):
        app.navigate_to("settings")


def test_show_is_a_jump_and_skips_guards(shell):
    app, view = shell
    app.show("Admin")
    assert app.current == "Admin"


def test_a_lazy_screen_is_not_built_until_it_is_reached_then_kept(shell):
    app, view = shell
    assert "root.reports" not in view._built.nodes and "reports" not in [r.view.lower() for r in view.handle.composition.routes if r.instance is not None]
    app.navigate_to("reports")
    app.window.advance(16)
    assert shown(view, "reports") == {"reports": True}
    app.window.simulate("click", node=view.node("root.reports.bump"))
    app.window.advance(16)
    app.navigate_to("")
    app.window.advance(16)
    assert shown(view, "reports", "home") == {"reports": False, "home": True}
    app.navigate_to("reports")
    assert view.handle.composition.find("root.reports") is not None


def test_a_lazy_screen_has_its_route_before_it_is_built(shell):
    app, view = shell
    assert app.location is not None
    app.navigate_to("reports")  # the route exists
    assert app.current == "Reports"


def test_a_lazy_route_with_if_is_refused(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Shell_View.tdl").write_text(
        """---
TDL: 0.2
Name: shell
---
Window {
  Name: shell
  Title: T
  Style { Width: 300, Height: 200 }
  Children {
    If <| True |> {
      Home {
        Name: home
        Route { Path: "", Lazy: true }
      }
    }
  }
}
""")
    (tmp_path / "Views" / "Home_View.tdl").write_text(LEAF.replace("NNN", "home"))
    with pytest.raises(LoadError, match="a lazy route takes no 'if:'"):
        App(root=tmp_path).open_view("Shell")


def test_a_route_mapping_is_checked(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Shell_View.tdl").write_text(
        """---
TDL: 0.2
Name: shell
---
Window {
  Name: shell
  Title: T
  Style { Width: 300, Height: 200 }
  Children {
    Home {
      Name: home
      Route { Path: "", Redirect: x }
    }
  }
}
""")
    (tmp_path / "Views" / "Home_View.tdl").write_text(LEAF.replace("NNN", "home"))
    with pytest.raises(LoadError, match="redirect"):
        App(root=tmp_path).open_view("Shell")


def _reloaded(app, view, tmp_path):
    """The window view edited (its title) and the view recomposed from the file, as the hot reload does."""
    import os

    from tess_ui.spec.watch import ComposedWatcher

    path = tmp_path / "Views" / "Shell_View.tdl"
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
    path.write_text(path.read_text().replace("Title: App", "Title: Edited"))
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
    assert watcher.poll() is True
    app.window.advance(16)


def test_a_reload_keeps_a_nested_current_screen_and_what_shows(shell, tmp_path):
    app, view = shell
    app.navigate_to("settings/profile")
    app.window.advance(16)
    before = shown(view, "home", "settings", "profile", "account")
    assert app.current == "Profile" and before == {"home": False, "settings": True, "profile": True, "account": False}
    _reloaded(app, view, tmp_path)
    assert app.current == "Profile" and shown(view, "home", "settings", "profile", "account") == before


def test_a_reload_builds_a_current_lazy_screen_again(shell, tmp_path):
    app, view = shell
    app.navigate_to("reports")
    app.window.advance(16)
    assert app.current == "Reports" and shown(view, "reports") == {"reports": True}
    _reloaded(app, view, tmp_path)
    assert app.current == "Reports" and shown(view, "reports") == {"reports": True}
