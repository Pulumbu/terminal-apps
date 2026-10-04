"""Behavioural tests driven through Textual's Pilot."""

from textual.widgets import DataTable, Input, Label, Switch

from nocturne.app import Nocturne
from nocturne.screens import Confirm, SettingsScreen
from nocturne.widgets import FilterableMultiSelect, WaveMeter


async def test_rows_load_and_status_updates():
    app = Nocturne(count=500)
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.5)
        table = app.screen.query_one("#rows", DataTable)
        assert table.row_count > 0
        assert "entries" in str(app.screen.query_one("#statusbar", Label).content)


async def test_search_debounces_and_filters():
    app = Nocturne(count=500)
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.5)
        before = app.screen.query_one("#rows", DataTable).row_count
        app.screen.query_one("#search", Input).value = "zzzz-no-match"
        await pilot.pause(0.5)
        after = app.screen.query_one("#rows", DataTable).row_count
        assert after == 0 and before > 0


async def test_multiselect_keeps_selection_across_filtering():
    app = Nocturne(count=200)
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.4)
        levels = app.screen.query_one("#levels", FilterableMultiSelect)
        levels.action_select_all()
        await pilot.pause()
        assert levels.selected == {"debug", "info", "warning", "error"}
        levels.query_one("#fms-search", Input).value = "err"
        await pilot.pause()
        assert levels.selected == {"debug", "info", "warning", "error"}
        levels.action_clear_all()
        await pilot.pause()
        assert levels.selected == set()


async def test_meter_animation_completes():
    app = Nocturne(count=100)
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.4)
        meter = app.screen.query_one("#meter", WaveMeter)
        meter.animate("value", 1.0, duration=0.1, easing="out_cubic")
        await pilot.wait_for_animation()
        assert meter.value == 1.0
        assert meter.phase > 0


async def test_theme_cycles_and_persists():
    app = Nocturne(count=100)
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.3)
        first = app.theme
        await pilot.press("ctrl+t")
        await pilot.pause(0.2)
        assert app.theme != first
        assert app.settings.theme == app.theme
        assert app.paths.settings_file.exists()


async def test_settings_modal_validates_and_saves():
    app = Nocturne(count=100)
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.3)
        app.action_settings()
        await pilot.pause(0.3)
        assert isinstance(app.screen, SettingsScreen)
        page_size = app.screen.query_one("#page-size", Input)
        page_size.value = "0"
        await pilot.pause()
        assert app.screen.query_one("#save").disabled
        page_size.value = "25"
        await pilot.pause()
        assert not app.screen.query_one("#save").disabled
        app.screen.query_one("#zebra", Switch).value = False
        await pilot.click("#save")
        await pilot.pause(0.3)
        assert app.settings.page_size == 25
        assert app.settings.flags["zebra"] is False
        assert app.screen.query_one("#rows", DataTable).zebra_stripes is False


async def test_confirm_modal_returns_a_value():
    app = Nocturne(count=100)
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.4)
        before = app.screen.query_one("#rows", DataTable).row_count
        app.action_confirm_delete()
        await pilot.pause(0.3)
        assert isinstance(app.screen, Confirm)
        await pilot.click("#yes")
        await pilot.pause(0.3)
        assert app.screen.query_one("#rows", DataTable).row_count == before - 1


async def test_breakpoints_hide_the_sidebar_when_narrow():
    app = Nocturne(count=100)
    async with app.run_test(size=(140, 36)) as pilot:
        await pilot.pause(0.3)
        assert app.screen.query_one("#sidebar").display
        await pilot.resize_terminal(70, 24)
        await pilot.pause(0.3)
        assert not app.screen.query_one("#sidebar").display


async def test_command_palette_provider_offers_commands():
    app = Nocturne(count=100)
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.3)
        app.filter_to_level("error")
        await pilot.pause(0.4)
        assert app.screen.query_one("#levels", FilterableMultiSelect).selected == {"error"}
