import threading
import time

from attack_shark_x11.app import (
    BATTERY_SIG,
    THEMES,
    battery_metrics,
    make_fin_icon,
    monitor_loop,
    parse_battery,
    render_chart,
    state_label,
    version_tuple,
)


def test_parse_battery_report():
    assert parse_battery([*BATTERY_SIG, 47]) == 47
    assert parse_battery([*BATTERY_SIG, 101]) is None
    assert parse_battery([0, 1, 2, 3, 47]) is None
    assert parse_battery(None) is None


def test_normal_wireless_state_is_connected():
    assert state_label("adapter", 75) == "Connected"
    assert state_label("adapter", 12, threshold=20) == "Low battery"
    assert "Discharging" not in state_label("adapter", 75)


def test_battery_metrics_estimate_and_rate():
    now = int(time.time())
    rows = [
        (now - 3600, 60, "adapter"),
        (now - 1800, 55, "adapter"),
        (now, 50, "adapter"),
    ]
    metrics = battery_metrics(rows, "adapter", 50, now)
    assert metrics.rate == "10.0% / h"
    assert metrics.estimate == "5h 00m"
    assert "remaining" in metrics.summary


def test_version_comparison_tuple():
    assert version_tuple("v1.2.3") == (1, 2, 3)
    assert version_tuple("2.0.0-beta.1") == (2, 0, 0)


def test_fin_icon_and_chart_render():
    icon = make_fin_icon("adapter", 47, size=64)
    assert icon.size == (64, 64)
    assert icon.mode == "RGBA"

    now = int(time.time())
    rows = [(now - 3600, 55, "adapter"), (now, 47, "adapter")]
    chart = render_chart(rows, 6 * 3600, now, width=640, height=280)
    assert chart.size == (640, 280)
    assert chart.mode == "RGBA"

    assert set(THEMES) == {
        "minimal_dark",
        "tech_blue",
        "modern_glass",
        "compact_pro",
    }
    for theme in THEMES.values():
        themed_chart = render_chart(
            rows, 6 * 3600, now, width=520, height=240, theme=theme
        )
        assert themed_chart.size == (520, 240)



def test_monitor_keeps_last_level_after_transient_hid_failure():
    stop_event = threading.Event()
    updates = []

    class FakeDevice:
        def __init__(self, generation):
            self.generation = generation
            self.read_count = 0

        def open_path(self, _path):
            pass

        def set_nonblocking(self, _value):
            pass

        def close(self):
            pass

        def read(self, _size):
            self.read_count += 1
            if self.generation == 1:
                if self.read_count == 1:
                    return [*BATTERY_SIG, 47]
                raise OSError("transient interface failure")

            if self.read_count >= 3:
                stop_event.set()
            return []

    class FakeHid:
        def __init__(self):
            self.generation = 0

        def enumerate(self, _vid, pid=None):
            if pid is None or pid == 0xFA60:
                return [{"path": b"fake"}]
            return []

        def device(self):
            self.generation += 1
            return FakeDevice(self.generation)

    monitor_loop(
        lambda mode, level, _changed: updates.append((mode, level)),
        stop_event,
        reenum_secs=0.01,
        heartbeat=0,
        hid_module=FakeHid(),
    )

    assert updates[0] == ("waiting", None)
    assert ("adapter", 47) in updates
    assert updates.count(("waiting", None)) == 1
    assert updates[-1] == ("adapter", 47)


def test_battery_metrics_uses_friendly_placeholders_while_learning():
    now = int(time.time())
    metrics = battery_metrics([(now, 93, "adapter")], "adapter", 93, now)
    assert metrics.estimate == "Learning"
    assert metrics.rate == "Monitoring"
    assert metrics.summary == "Collecting battery history"


def test_battery_metrics_reports_stable_without_calculating_label():
    now = int(time.time())
    rows = [
        (now - 900, 93, "adapter"),
        (now - 450, 93, "adapter"),
        (now, 93, "adapter"),
    ]
    metrics = battery_metrics(rows, "adapter", 93, now)
    assert metrics.estimate == "Pending"
    assert metrics.rate == "Stable"
    assert "measurable battery change" in metrics.summary
