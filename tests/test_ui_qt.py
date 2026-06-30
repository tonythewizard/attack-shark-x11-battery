import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from attack_shark_x11.app import App
from attack_shark_x11.ui_qt import DashboardWindow, PreviewController, THEMES


def _qt_app():
    return QApplication.instance() or QApplication(["attack-shark-x11-test"])


def test_all_qt_themes_build_and_render():
    app = _qt_app()
    for key in THEMES:
        window = DashboardWindow(PreviewController(), preview_theme=key)
        window.resize(960, 640)
        window.show()
        app.processEvents()
        image = window.grab().toImage()
        assert not image.isNull()
        assert image.width() == 960
        assert image.height() == 640
        assert window.theme_key == key
        assert window.theme_combo.count() == 4
        window.deleteLater()
        app.processEvents()


def test_tray_double_click_opens_dashboard():
    controller = object.__new__(App)
    called = []
    controller._open = lambda *_: called.append(True)
    controller._tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
    assert called == [True]


def test_theme_switches_replace_surface_without_blank_ui():
    app = _qt_app()
    window = DashboardWindow(PreviewController(), preview_theme="minimal_dark")
    window.resize(960, 640)
    window.show()
    app.processEvents()

    previous_content = window.content
    for key in ("tech_blue", "modern_glass", "compact_pro", "minimal_dark"):
        index = window.theme_combo.findData(key)
        assert index >= 0
        window.theme_combo.setCurrentIndex(index)
        # The switch is queued to avoid deleting a live QComboBox signal target.
        for _ in range(3):
            app.processEvents()
        assert window.theme_key == key
        assert window.content is not previous_content
        assert window.content.isVisible()
        assert window.content.layout() is not None
        assert window.chart is not None
        image = window.grab().toImage()
        assert not image.isNull()
        previous_content = window.content

    window.deleteLater()
    app.processEvents()


def test_compact_gauge_renders_with_safe_inset():
    from attack_shark_x11.ui_qt import BatteryGauge, THEMES

    _qt_app()
    gauge = BatteryGauge(THEMES["compact_pro"], compact=True, show_caption=False)
    gauge.setFixedSize(102, 92)
    ring, stroke, glow_extra = gauge._ring_geometry()
    outer = (stroke + glow_extra) / 2.0
    assert ring.left() - outer > 0
    assert ring.top() - outer > 0
    assert ring.right() + outer < gauge.width()
    assert ring.bottom() + outer < gauge.height()

