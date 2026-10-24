"""PySide6 dashboard for Attack Shark X11.

The widgets in this module are intentionally drawn with QPainter instead of
bitmap-heavy Tk widgets.  This keeps rings, charts, icons, and rounded cards
sharp at every Windows scaling level.
"""

from __future__ import annotations

import math
import os
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QBrush,
    QConicalGradient,
    QIcon,
    QImage,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .app import (
    APP_NAME,
    REPO_URL,
    THEME_ORDER,
    battery_metrics,
    make_fin_icon,
    settings_load,
    settings_save,
    startup_get,
    startup_set,
    state_label,
    status_color,
)


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    layout: str
    accent: str
    accent_2: str
    window: str
    shell: str
    surface: str
    surface_2: str
    surface_3: str
    border: str
    border_soft: str
    text: str
    muted: str
    muted_2: str
    track: str
    chart_grid: str
    chart_plot: str
    chart_fill_alpha: int
    estimate_accent: str
    rate_accent: str
    radius: int = 12


THEMES: dict[str, Theme] = {
    "minimal_dark": Theme(
        key="minimal_dark",
        name="Minimal Dark",
        layout="minimal",
        accent="#3DDC84",
        accent_2="#57E497",
        window="#080C12",
        shell="#0B0F15",
        surface="#111722",
        surface_2="#151C28",
        surface_3="#0E141E",
        border="#293241",
        border_soft="#202937",
        text="#F3F6FA",
        muted="#8E99AA",
        muted_2="#697586",
        track="#394352",
        chart_grid="#2A3442",
        chart_plot="#0E141E",
        chart_fill_alpha=70,
        estimate_accent="#4C8DFF",
        rate_accent="#FF9A55",
    ),
    "tech_blue": Theme(
        key="tech_blue",
        name="Tech Blue",
        layout="tech",
        accent="#1597FF",
        accent_2="#54B8FF",
        window="#020711",
        shell="#050B16",
        surface="#071426",
        surface_2="#091A31",
        surface_3="#050F1E",
        border="#145FA5",
        border_soft="#103C6A",
        text="#F4FAFF",
        muted="#7F9DBD",
        muted_2="#557696",
        track="#163A59",
        chart_grid="#153352",
        chart_plot="#050F1E",
        chart_fill_alpha=84,
        estimate_accent="#3B9CFF",
        rate_accent="#38CEFF",
        radius=10,
    ),
    "modern_glass": Theme(
        key="modern_glass",
        name="Modern Glass",
        layout="glass",
        accent="#FF7A21",
        accent_2="#FFAE65",
        window="#090A10",
        shell="#101119",
        surface="#181824",
        surface_2="#211D2A",
        surface_3="#111219",
        border="#493A4F",
        border_soft="#352C3C",
        text="#FFF8F3",
        muted="#A8A0AB",
        muted_2="#736C79",
        track="#453946",
        chart_grid="#3A303E",
        chart_plot="#111219",
        chart_fill_alpha=92,
        estimate_accent="#3AA7FF",
        rate_accent="#FF8A2E",
        radius=16,
    ),
    "compact_pro": Theme(
        key="compact_pro",
        name="Compact Pro",
        layout="compact",
        accent="#A44FFF",
        accent_2="#C17BFF",
        window="#070811",
        shell="#090B13",
        surface="#111421",
        surface_2="#171A2A",
        surface_3="#0D101A",
        border="#303553",
        border_soft="#24283F",
        text="#F7F4FF",
        muted="#9295AA",
        muted_2="#656980",
        track="#34384D",
        chart_grid="#2A2E45",
        chart_plot="#0D101A",
        chart_fill_alpha=82,
        estimate_accent="#9C5CFF",
        rate_accent="#FF7748",
        radius=10,
    ),
    "obsidian": Theme(
        key="obsidian", name="Obsidian", layout="minimal",
        accent="#C5A46D", accent_2="#E2C99C", window="#080A0D", shell="#0E1116",
        surface="#161B22", surface_2="#1C222B", surface_3="#10151B",
        border="#3B434F", border_soft="#28313B", text="#F2F2EF", muted="#9DA6B1",
        muted_2="#788391", track="#323B45", chart_grid="#28313C",
        chart_plot="#0F141B", chart_fill_alpha=38,
        estimate_accent="#9CB2C8", rate_accent="#C5A46D", radius=14,
    ),
    "arctic": Theme(
        key="arctic", name="Arctic Light", layout="glass",
        accent="#2563EB", accent_2="#60A5FA", window="#EEF2F7", shell="#F5F7FB",
        surface="#FFFFFF", surface_2="#EAF0F8", surface_3="#F7F9FC",
        border="#C9D6E6", border_soft="#D8E1ED", text="#14243A", muted="#53667F",
        muted_2="#71839A", track="#CED8E5", chart_grid="#DEE6F0",
        chart_plot="#F5F8FD", chart_fill_alpha=32,
        estimate_accent="#3278BA", rate_accent="#D18B45", radius=14,
    ),
    "graphite": Theme(
        key="graphite", name="Graphite Studio", layout="compact",
        accent="#8AA4BF", accent_2="#B8CADC", window="#101214", shell="#171A1E",
        surface="#20252A", surface_2="#252B32", surface_3="#171B20",
        border="#424A53", border_soft="#323940", text="#EDF0F3", muted="#A4ADB8",
        muted_2="#7B8793", track="#424A53", chart_grid="#343C45",
        chart_plot="#14191E", chart_fill_alpha=28,
        estimate_accent="#92B2B1", rate_accent="#BEA585", radius=10,
    ),
    "midnight": Theme(
        key="midnight", name="Midnight Slate", layout="tech",
        accent="#6D8CF7", accent_2="#9AB0FF", window="#080D18", shell="#0C1321",
        surface="#121D2F", surface_2="#17253B", surface_3="#0F1829",
        border="#344967", border_soft="#253953", text="#F3F6FE", muted="#A7B5CD",
        muted_2="#7185A3", track="#344965", chart_grid="#243953",
        chart_plot="#0D1626", chart_fill_alpha=48,
        estimate_accent="#6FBFC8", rate_accent="#E2A979", radius=12,
    ),
}


def _qcolor(value: str | tuple[int, int, int], alpha: Optional[int] = None) -> QColor:
    color = QColor(value) if isinstance(value, str) else QColor(*value)
    if alpha is not None:
        color.setAlpha(alpha)
    return color


def _css_rgba(value: str, alpha: int) -> str:
    color = QColor(value)
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {max(0, min(255, alpha))})"


def pil_to_qpixmap(image: Any) -> QPixmap:
    """Convert a Pillow RGBA image to a detached Qt pixmap."""
    rgba = image.convert("RGBA")
    raw = rgba.tobytes("raw", "RGBA")
    qimage = QImage(raw, rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


def fin_pixmap(mode: str, level: Optional[int], size: int) -> QPixmap:
    source = make_fin_icon(mode, level, size=max(128, size * 3))
    return pil_to_qpixmap(source).scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def status_accent(theme: Theme, mode: str, level: Optional[int], threshold: int) -> QColor:
    del theme
    if mode == "adapter" and level is not None and level > threshold:
        return QColor("#3DDC84")
    return _qcolor(status_color(mode, level))


def gauge_accent(theme: Theme, mode: str, level: Optional[int], threshold: int) -> QColor:
    if mode == "adapter" and level is not None and level > threshold:
        return QColor(theme.accent)
    return _qcolor(status_color(mode, level))


class ClickLabel(QLabel):
    clicked = Signal()

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class Card(QFrame):
    def __init__(
        self,
        theme: Theme,
        *,
        alt: bool = False,
        radius: Optional[int] = None,
        glow: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.theme = theme
        self.alt = alt
        self.radius = theme.radius if radius is None else radius
        self.glow = glow
        self.setObjectName("asxCard")
        self.apply_theme(theme)

    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        bg = theme.surface_2 if self.alt else theme.surface
        # Semi-transparent cards allow the painted atmospheric background to
        # remain visible without sacrificing text contrast.  Modern Glass is
        # intentionally more translucent than the other profiles.
        alpha = 204 if theme.key == "modern_glass" else 228
        if theme.key == "modern_glass":
            end = theme.surface if self.alt else theme.surface_3
            background = (
                "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                f"stop:0 {_css_rgba(bg, alpha)}, "
                f"stop:0.52 {_css_rgba(theme.surface_2, alpha - 10)}, "
                f"stop:1 {_css_rgba(end, alpha - 22)})"
            )
            background_rule = f"background: {background};"
        elif theme.key == "tech_blue":
            background_rule = (
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                f"stop:0 {_css_rgba(bg, alpha)}, stop:1 {_css_rgba(theme.surface_3, alpha - 12)});"
            )
        else:
            background_rule = f"background-color: {_css_rgba(bg, alpha)};"
        self.setStyleSheet(
            f"QFrame#asxCard {{ {background_rule} border: 1px solid {theme.border_soft}; "
            f"border-radius: {self.radius}px; }}"
        )
        if self.glow:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(22)
            shadow.setOffset(0, 3)
            shadow.setColor(_qcolor(theme.accent, 35))
            self.setGraphicsEffect(shadow)


class AtmosphereSurface(QWidget):
    """Translucent, theme-aware background painted behind the dashboard.

    The design deliberately avoids bitmap assets: gradients, soft glows,
    circuit lines and glass ribbons remain crisp at every DPI and window size.
    """

    def __init__(self, theme: Theme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.update()

    def paintEvent(self, _event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        if rect.isEmpty():
            return

        # Translucent base: enough opacity for readability, while still
        # allowing the desktop/window backdrop to subtly influence the UI.
        base_alpha = 218 if self.theme.key == "modern_glass" else 236
        painter.fillRect(rect, _qcolor(self.theme.shell, base_alpha))

        w, h = rect.width(), rect.height()
        accent = QColor(self.theme.accent)
        accent2 = QColor(self.theme.accent_2)

        # Large soft light fields.
        glow1 = QRadialGradient(QPointF(w * 0.10, h * 0.12), max(w, h) * 0.58)
        glow1.setColorAt(0.0, _qcolor(accent.name(), 46 if self.theme.key == "modern_glass" else 30))
        glow1.setColorAt(0.42, _qcolor(accent.name(), 14))
        glow1.setColorAt(1.0, _qcolor(accent.name(), 0))
        painter.fillRect(rect, QBrush(glow1))

        glow2 = QRadialGradient(QPointF(w * 0.92, h * 0.86), max(w, h) * 0.55)
        glow2.setColorAt(0.0, _qcolor(accent2.name(), 34 if self.theme.key == "modern_glass" else 20))
        glow2.setColorAt(0.52, _qcolor(accent2.name(), 9))
        glow2.setColorAt(1.0, _qcolor(accent2.name(), 0))
        painter.fillRect(rect, QBrush(glow2))

        # A broad translucent ribbon gives the background depth without
        # becoming a simple flat gradient.
        ribbon = QPainterPath()
        ribbon.moveTo(-w * 0.05, h * 0.66)
        ribbon.cubicTo(w * 0.22, h * 0.48, w * 0.43, h * 0.88, w * 0.70, h * 0.62)
        ribbon.cubicTo(w * 0.84, h * 0.49, w * 0.94, h * 0.52, w * 1.08, h * 0.39)
        ribbon.lineTo(w * 1.08, h * 0.58)
        ribbon.cubicTo(w * 0.82, h * 0.75, w * 0.66, h * 0.74, w * 0.49, h * 0.83)
        ribbon.cubicTo(w * 0.27, h * 0.94, w * 0.13, h * 0.69, -w * 0.05, h * 0.83)
        ribbon.closeSubpath()
        ribbon_gradient = QLinearGradient(0, h * 0.45, w, h * 0.80)
        ribbon_gradient.setColorAt(0.0, _qcolor(accent.name(), 0))
        ribbon_gradient.setColorAt(0.38, _qcolor(accent.name(), 14))
        ribbon_gradient.setColorAt(0.72, _qcolor(accent2.name(), 22 if self.theme.key == "modern_glass" else 12))
        ribbon_gradient.setColorAt(1.0, _qcolor(accent2.name(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ribbon_gradient)
        painter.drawPath(ribbon)

        # Theme-specific line language.
        if self.theme.key == "tech_blue":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for offset in (0.0, 18.0, 36.0):
                path = QPainterPath(QPointF(w * 0.58, 34 + offset))
                path.lineTo(w * 0.76, 34 + offset)
                path.lineTo(w * 0.80, 14 + offset)
                path.lineTo(w * 0.98, 14 + offset)
                painter.setPen(QPen(_qcolor(accent.name(), 34 - int(offset / 2)), 1.0))
                painter.drawPath(path)
        elif self.theme.key == "modern_glass":
            # Two crossed glass caustics, kept very subtle under the cards.
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(3):
                path = QPainterPath(QPointF(-20, h * (0.22 + i * 0.13)))
                path.cubicTo(w * 0.30, h * (0.04 + i * 0.10), w * 0.58, h * (0.52 + i * 0.05), w + 20, h * (0.24 + i * 0.10))
                painter.setPen(QPen(_qcolor(accent2.name(), 25 - i * 6), 1.2))
                painter.drawPath(path)
        elif self.theme.key == "compact_pro":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(-3, 9):
                x = i * 120.0
                painter.setPen(QPen(_qcolor(accent.name(), 11), 1.0))
                painter.drawLine(QPointF(x, h), QPointF(x + h * 0.58, 0))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for radius, alpha in ((190, 18), (260, 11), (340, 7)):
                painter.setPen(QPen(_qcolor(accent.name(), alpha), 1.0))
                painter.drawArc(QRectF(-radius * 0.38, -radius * 0.43, radius, radius), 205 * 16, 155 * 16)

        # Fine dot field: visible only on close inspection.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_qcolor(self.theme.text, 10))
        step = 34
        for y in range(24, int(h), step):
            shift = 17 if (y // step) % 2 else 0
            for x in range(20 + shift, int(w), step):
                painter.drawEllipse(QPointF(x, y), 0.75, 0.75)


class StatusDot(QWidget):
    def __init__(self, color: str, diameter: int = 10, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = QColor(color)
        self._diameter = diameter
        self.setFixedSize(diameter + 8, diameter + 8)

    def set_color(self, color: QColor | str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = self.rect().center()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_qcolor(self._color.name(), 45))
        painter.drawEllipse(center, self._diameter // 2 + 3, self._diameter // 2 + 3)
        painter.setBrush(self._color)
        painter.drawEllipse(center, self._diameter // 2, self._diameter // 2)


class TinyIcon(QWidget):
    def __init__(self, kind: str, color: str, size: int = 27, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.kind = kind
        self._color = QColor(color)
        self.setFixedSize(size, size)

    def set_color(self, color: str | QColor) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(
            QPen(
                self._color,
                1.8,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        r = QRectF(4.5, 4.5, self.width() - 9, self.height() - 9)
        if self.kind == "status":
            painter.drawEllipse(r)
            painter.drawLine(QPointF(8, 14), QPointF(12, 18))
            painter.drawLine(QPointF(12, 18), QPointF(20, 9))
        elif self.kind == "clock":
            painter.drawEllipse(r)
            cx, cy = r.center().x(), r.center().y()
            painter.drawLine(QPointF(cx, r.top() + 4), QPointF(cx, cy + 1))
            painter.drawLine(QPointF(cx, cy + 1), QPointF(cx + 5, cy + 4))
        elif self.kind == "rate":
            mid = self.height() / 2
            path = QPainterPath(QPointF(3, mid + 3))
            path.lineTo(8, mid + 3)
            path.lineTo(11, mid - 5)
            path.lineTo(15, mid + 8)
            path.lineTo(19, mid - 1)
            path.lineTo(self.width() - 3, mid - 1)
            painter.drawPath(path)
        elif self.kind == "link":
            painter.drawArc(QRectF(3, 8, 14, 12), 35 * 16, 245 * 16)
            painter.drawArc(QRectF(10, 6, 14, 12), 215 * 16, 245 * 16)


class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, theme: Theme, checked: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.theme = theme
        self._checked = checked
        self.setFixedSize(42, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        checked = bool(checked)
        if checked != self._checked:
            self._checked = checked
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)
        super().mouseReleaseEvent(event)

    def paintEvent(self, _event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QColor(self.theme.accent if self._checked else self.theme.track)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(0, 2, 42, 20), 10, 10)
        painter.setBrush(QColor("#FFFFFF"))
        x = 22 if self._checked else 3
        painter.drawEllipse(QRectF(x, 3, 18, 18))


class BatteryGauge(QWidget):
    """Antialiased circular battery gauge used by the non-minimal layouts."""

    def __init__(
        self,
        theme: Theme,
        *,
        compact: bool = False,
        show_caption: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.theme = theme
        self.mode = "loading"
        self.level: Optional[int] = None
        self.threshold = 20
        self.compact = compact
        self.show_caption = show_caption
        self.setMinimumSize(145 if compact else 180, 120 if compact else 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_state(self, mode: str, level: Optional[int], threshold: int) -> None:
        self.mode, self.level, self.threshold = mode, level, threshold
        self.update()

    def _display_text(self) -> str:
        if self.mode == "adapter" and self.level is not None:
            return f"{self.level}%"
        if self.mode == "charging":
            return "⚡"
        if self.mode in ("loading", "waiting"):
            return "..."
        return "N/A"

    def _ring_geometry(self) -> tuple[QRectF, float, float]:
        caption_space = 0 if not self.show_caption else (32 if self.compact else 48)
        available_h = max(1.0, self.height() - caption_space)
        available_side = min(float(self.width()), float(available_h))
        margin = 5.0 if self.compact else 10.0
        provisional = max(48.0, available_side - margin * 2.0)
        width = max(6.0, provisional * (0.075 if self.compact else 0.065))
        glow_extra = 7.0
        safe_inset = margin + (width + glow_extra) / 2.0
        diameter = max(44.0, min(
            self.width() - safe_inset * 2.0,
            available_h - safe_inset * 2.0,
        ))
        ring = QRectF(
            (self.width() - diameter) / 2.0,
            (available_h - diameter) / 2.0,
            diameter,
            diameter,
        )
        return ring, width, glow_extra

    def paintEvent(self, _event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Keep the complete active stroke and its glow inside the widget.
        # The previous hard minimum diameter could exceed compact widgets and
        # Qt clipped the glow into a visible straight line / rectangle.
        ring, width, glow_extra = self._ring_geometry()
        diameter = ring.width()

        painter.setPen(QPen(QColor(self.theme.track), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(ring, 90 * 16, -360 * 16)

        accent = gauge_accent(self.theme, self.mode, self.level, self.threshold)
        span = 360.0
        if self.mode == "adapter" and self.level is not None:
            span = max(3.0, 360.0 * self.level / 100.0)
        elif self.mode in ("loading", "waiting"):
            span = 82.0
        elif self.mode == "disconnected":
            span = 20.0

        glow = QPen(_qcolor(accent.name(), 42), width + 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(glow)
        painter.drawArc(ring, 90 * 16, int(-span * 16))
        if self.theme.key == "modern_glass" and self.mode == "adapter" and self.level is not None and self.level > self.threshold:
            gradient = QConicalGradient(ring.center(), 90)
            gradient.setColorAt(0.0, QColor("#FF7A21"))
            gradient.setColorAt(0.45, QColor("#F7B32B"))
            gradient.setColorAt(0.78, QColor("#39D27D"))
            gradient.setColorAt(1.0, QColor("#FF7A21"))
            active_pen = QPen(QBrush(gradient), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        else:
            active_pen = QPen(accent, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(active_pen)
        painter.drawArc(ring, 90 * 16, int(-span * 16))

        fin_size = int(diameter * (0.25 if self.compact else 0.28))
        fin = fin_pixmap(self.mode, self.level, fin_size)
        fin_rect = QRectF(
            ring.center().x() - fin_size / 2,
            ring.center().y() - diameter * 0.20,
            fin_size,
            fin_size,
        )
        painter.drawPixmap(fin_rect.toRect(), fin)

        text_rect = QRectF(ring.left(), ring.center().y() - 2, ring.width(), diameter * 0.34)
        font = QFont("Segoe UI", max(17, int(diameter * (0.18 if self.compact else 0.20))))
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(self.theme.text))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._display_text())

        if self.show_caption:
            caption = state_label(self.mode, self.level, self.threshold)
            caption_rect = QRectF(0, ring.bottom() + 8, self.width(), 24)
            font = QFont("Segoe UI", 11 if self.compact else 13)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.setPen(status_accent(self.theme, self.mode, self.level, self.threshold))
            painter.drawText(caption_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, caption)


class BatteryChart(QWidget):
    range_changed = Signal(object)

    def __init__(self, theme: Theme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.history: list[tuple[int, Optional[int], str]] = []
        self.range_secs: Optional[int] = 24 * 3600
        self.now = time.time()
        self.setMinimumHeight(230)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.update()

    def set_data(
        self,
        history: Sequence[tuple[int, Optional[int], str]],
        range_secs: Optional[int],
        now: Optional[float] = None,
    ) -> None:
        self.history = list(history)
        self.range_secs = range_secs
        self.now = time.time() if now is None else now
        self.update()

    def _valid_points(self) -> list[tuple[float, int, str]]:
        valid = [
            (float(ts), int(level), state)
            for ts, level, state in self.history
            if level is not None and 0 <= int(level) <= 100
        ]
        if not valid:
            return []
        if self.range_secs is None:
            start = valid[0][0]
        else:
            start = self.now - self.range_secs
        points = [row for row in valid if row[0] >= start]
        if not points:
            points = [valid[-1]]
        return points

    @staticmethod
    def _time_label(timestamp: float, span: float) -> str:
        tm = time.localtime(timestamp)
        if span > 10 * 24 * 3600:
            return time.strftime("%d %b", tm)
        return time.strftime("%H:%M", tm)

    def paintEvent(self, _event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        left, right, top, bottom = 52, 18, 12, 34
        plot = QRectF(left, top, max(40, self.width() - left - right), max(50, self.height() - top - bottom))
        painter.setPen(QPen(QColor(self.theme.border_soft), 1))
        painter.setBrush(QColor(self.theme.chart_plot))
        painter.drawRoundedRect(plot, 8, 8)

        grid_pen = QPen(QColor(self.theme.chart_grid), 1)
        grid_pen.setCosmetic(True)
        painter.setFont(QFont("Segoe UI", 8))
        for pct in (100, 75, 50, 25, 0):
            y = plot.top() + (100 - pct) / 100 * plot.height()
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(QColor(self.theme.muted))
            painter.drawText(
                QRectF(0, y - 9, left - 10, 18),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(pct),
            )

        points = self._valid_points()
        if points:
            if self.range_secs is None:
                start = points[0][0]
                end = max(self.now, points[-1][0])
            else:
                start = self.now - self.range_secs
                end = self.now
        else:
            end = self.now
            start = self.now - (self.range_secs or 24 * 3600)
        if end <= start:
            end = start + 1
        span = end - start

        for i in range(5):
            x = plot.left() + i / 4 * plot.width()
            if i not in (0, 4):
                painter.setPen(grid_pen)
                painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            label = self._time_label(start + i / 4 * span, span)
            painter.setPen(QColor(self.theme.muted))
            align = Qt.AlignmentFlag.AlignHCenter
            if i == 0:
                align = Qt.AlignmentFlag.AlignLeft
            elif i == 4:
                align = Qt.AlignmentFlag.AlignRight
            painter.drawText(
                QRectF(x - 50, plot.bottom() + 8, 100, 18),
                align | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        if not points:
            painter.setPen(QColor(self.theme.muted_2))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "Waiting for battery history")
            return

        def px(ts: float) -> float:
            return plot.left() + max(0.0, min(1.0, (ts - start) / span)) * plot.width()

        def py(level: int) -> float:
            return plot.bottom() - max(0, min(100, level)) / 100 * plot.height()

        path = QPainterPath()
        qpoints: list[QPointF] = []
        for index, (timestamp, level, _state) in enumerate(points):
            point = QPointF(px(timestamp), py(level))
            qpoints.append(point)
            if index == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)

        accent = QColor(self.theme.accent)
        fill = QPainterPath(path)
        fill.lineTo(qpoints[-1].x(), plot.bottom())
        fill.lineTo(qpoints[0].x(), plot.bottom())
        fill.closeSubpath()
        gradient = QLinearGradient(0, plot.top(), 0, plot.bottom())
        gradient.setColorAt(0.0, _qcolor(accent.name(), self.theme.chart_fill_alpha))
        gradient.setColorAt(0.72, _qcolor(accent.name(), max(10, self.theme.chart_fill_alpha // 5)))
        gradient.setColorAt(1.0, _qcolor(accent.name(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawPath(fill)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_qcolor(accent.name(), 48), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)
        painter.setPen(QPen(accent, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)

        end_point = qpoints[-1]
        painter.setPen(QPen(QColor("#E8FFF3"), 1.5))
        painter.setBrush(accent)
        painter.drawEllipse(end_point, 5, 5)


class RangeSelector(QWidget):
    changed = Signal(object)

    RANGES: tuple[tuple[str, Optional[int]], ...] = (
        ("1h", 3600),
        ("6h", 6 * 3600),
        ("24h", 24 * 3600),
        ("7d", 7 * 24 * 3600),
        ("All", None),
    )

    def __init__(self, theme: Theme, current: Optional[int] = 24 * 3600, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.theme = theme
        self.current = current
        self.buttons: dict[Optional[int], QPushButton] = {}
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        for label, value in self.RANGES:
            button = QPushButton(label)
            button.setFixedSize(45, 29)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, item=value: self.set_value(item, emit=True))
            row.addWidget(button)
            self.buttons[value] = button
        self._restyle()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._restyle()

    def set_value(self, value: Optional[int], *, emit: bool = False) -> None:
        self.current = value
        self._restyle()
        if emit:
            self.changed.emit(value)

    def _restyle(self) -> None:
        for value, button in self.buttons.items():
            active = value == self.current
            bg = self.theme.accent if active else self.theme.surface_2
            border = self.theme.accent_2 if active else self.theme.border_soft
            fg = "#FFFFFF" if active else self.theme.text
            button.setStyleSheet(
                f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {border}; "
                "border-radius: 7px; font-size: 10px; font-weight: 600; padding: 0; }"
                f"QPushButton:hover {{ background: {self.theme.accent_2 if active else self.theme.surface_3}; }}"
            )


class StatCard(Card):
    def __init__(
        self,
        theme: Theme,
        kind: str,
        title: str,
        *,
        compact: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(theme, radius=9 if compact else 10, parent=parent)
        self.kind = kind
        self.title_text = title
        self.compact = compact
        self.icon = TinyIcon(kind, theme.accent if kind == "status" else (theme.estimate_accent if kind == "clock" else theme.rate_accent), 24 if compact else 28)
        self.title = QLabel(title)
        self.value = QLabel("Waiting")
        self.caption = QLabel("")
        self.caption.setVisible(not compact)

        row = QHBoxLayout(self)
        row.setContentsMargins(14 if compact else 17, 10 if compact else 13, 14 if compact else 17, 10 if compact else 13)
        row.setSpacing(9 if compact else 12)
        row.addWidget(self.icon)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(self.title)
        col.addWidget(self.value)
        col.addWidget(self.caption)
        row.addLayout(col, 1)
        self.apply_theme(theme)

    def apply_theme(self, theme: Theme) -> None:
        super().apply_theme(theme)
        self.theme = theme
        if not hasattr(self, "title"):
            return
        icon_color = theme.accent if self.kind == "status" else (theme.estimate_accent if self.kind == "clock" else theme.rate_accent)
        self.icon.set_color(icon_color)
        self.title.setStyleSheet(f"color: {theme.muted}; font-size: 9px; font-weight: 700; letter-spacing: 0.6px;")
        self.value.setStyleSheet(f"color: {theme.text}; font-size: {'15' if self.compact else '17'}px; font-weight: 700;")
        self.caption.setStyleSheet(f"color: {theme.muted}; font-size: 9px;")

    def set_value(self, value: str, caption: str = "", color: Optional[QColor | str] = None) -> None:
        self.value.setText(value)
        self.caption.setText(caption)
        chosen = QColor(color).name() if color is not None else self.theme.text
        self.value.setStyleSheet(f"color: {chosen}; font-size: {'15' if self.compact else '17'}px; font-weight: 700;")


class HeroStrip(Card):
    def __init__(self, theme: Theme, parent: Optional[QWidget] = None) -> None:
        super().__init__(theme, radius=12, parent=parent)
        self.setFixedHeight(112)
        row = QHBoxLayout(self)
        row.setContentsMargins(24, 17, 24, 17)
        row.setSpacing(17)

        self.fin = QLabel()
        self.fin.setFixedSize(64, 64)
        self.fin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.fin)

        self.percent = QLabel("...")
        self.percent.setMinimumWidth(135)
        row.addWidget(self.percent)

        status_col = QVBoxLayout()
        status_col.setSpacing(3)
        status_col.addStretch()
        status_row = QHBoxLayout()
        status_row.setSpacing(7)
        self.status = QLabel("Loading device...")
        self.dot = StatusDot(theme.accent)
        status_row.addWidget(self.status)
        status_row.addWidget(self.dot)
        status_row.addStretch()
        status_col.addLayout(status_row)
        self.subtitle = QLabel("Checking mouse status")
        status_col.addWidget(self.subtitle)
        status_col.addStretch()
        row.addLayout(status_col, 1)

        brand_col = QVBoxLayout()
        brand_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        b1 = QLabel("ATTACK SHARK X11")
        b1.setAlignment(Qt.AlignmentFlag.AlignRight)
        b2 = QLabel("Battery monitor")
        b2.setAlignment(Qt.AlignmentFlag.AlignRight)
        brand_col.addWidget(b1)
        brand_col.addWidget(b2)
        row.addLayout(brand_col)
        self.brand_title, self.brand_subtitle = b1, b2
        self.apply_theme(theme)

    def apply_theme(self, theme: Theme) -> None:
        super().apply_theme(theme)
        self.theme = theme
        if not hasattr(self, "percent"):
            return
        self.percent.setStyleSheet(f"color: {theme.text}; font-size: 48px; font-weight: 800; letter-spacing: -1px;")
        self.status.setStyleSheet(f"color: {theme.accent}; font-size: 17px; font-weight: 700;")
        self.subtitle.setStyleSheet(f"color: {theme.muted}; font-size: 11px;")
        self.brand_title.setStyleSheet(f"color: {theme.text}; font-size: 11px; font-weight: 700;")
        self.brand_subtitle.setStyleSheet(f"color: {theme.muted}; font-size: 10px;")

    def set_state(self, mode: str, level: Optional[int], threshold: int, status: str, subtitle: str) -> None:
        accent = status_accent(self.theme, mode, level, threshold)
        self.fin.setPixmap(fin_pixmap(mode, level, 60))
        if mode == "adapter" and level is not None:
            self.percent.setText(f"{level}%")
        elif mode == "charging":
            self.percent.setText("⚡")
        elif mode in ("loading", "waiting"):
            self.percent.setText("...")
        else:
            self.percent.setText("N/A")
        self.status.setText(status)
        self.subtitle.setText(subtitle)
        self.status.setStyleSheet(f"color: {accent.name()}; font-size: 17px; font-weight: 700;")
        self.dot.set_color(accent)


class TitleBar(QFrame):
    def __init__(self, window: "DashboardWindow", theme: Theme) -> None:
        super().__init__(window)
        self.window_ref = window
        self.theme = theme
        self._dragging = False
        self.setObjectName("titleBar")
        self.setFixedHeight(38)
        row = QHBoxLayout(self)
        row.setContentsMargins(13, 0, 7, 0)
        row.setSpacing(8)

        self.icon = QLabel()
        self.icon.setFixedSize(18, 18)
        row.addWidget(self.icon)
        self.title = QLabel(APP_NAME)
        row.addWidget(self.title)
        row.addStretch()

        self.min_btn = QPushButton("—")
        self.close_btn = QPushButton("×")
        for button in (self.min_btn, self.close_btn):
            button.setFixedSize(40, 28)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(button)
        self.min_btn.clicked.connect(window.showMinimized)
        self.close_btn.clicked.connect(window.hide_to_tray)
        self.apply_theme(theme)

    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.setStyleSheet(
            f"QFrame#titleBar {{ background: {_css_rgba(theme.shell, 232)}; border: none; }}"
        )
        self.title.setStyleSheet(f"color: {theme.text}; font-size: 11px; font-weight: 600;")
        common = (
            f"QPushButton {{ color: {theme.muted}; background: transparent; border: none; border-radius: 6px; font-size: 18px; }}"
            f"QPushButton:hover {{ color: {theme.text}; background: {theme.surface_2}; }}"
        )
        self.min_btn.setStyleSheet(common)
        self.close_btn.setStyleSheet(
            f"QPushButton {{ color: {theme.muted}; background: transparent; border: none; border-radius: 6px; font-size: 18px; }}"
            "QPushButton:hover { color: white; background: #C42B1C; }"
        )

    def set_icon(self, pixmap: QPixmap) -> None:
        self.icon.setPixmap(pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            handle = self.window_ref.windowHandle()
            if handle is not None and hasattr(handle, "startSystemMove"):
                handle.startSystemMove()
                self._dragging = False
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.window_ref.isMaximized():
                self.window_ref.showNormal()
            else:
                self.window_ref.showMaximized()
        super().mouseDoubleClickEvent(event)


class DashboardWindow(QWidget):
    """Main dashboard. The application object supplies live state and actions."""

    theme_changed = Signal(str)

    def __init__(self, app_controller: Any, *, preview_theme: Optional[str] = None) -> None:
        super().__init__()
        self.controller = app_controller
        saved = str(settings_load().get("theme", "minimal_dark"))
        self.theme_key = preview_theme if preview_theme in THEMES else (saved if saved in THEMES else "minimal_dark")
        self.theme = THEMES[self.theme_key]
        self.range_secs: Optional[int] = 24 * 3600
        self._loading_frame = 0
        self._last_icon_state: Optional[tuple[str, Optional[int]]] = None
        self._resizing_edge = Qt.Edge(0)
        self._theme_switch_pending = False

        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.resize(1080, 720)
        self.setMinimumSize(920, 620)

        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(8, 8, 8, 8)
        self.outer.setSpacing(0)
        self.shell = QFrame()
        self.shell.setObjectName("shell")
        shadow = QGraphicsDropShadowEffect(self.shell)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 155))
        self.shell.setGraphicsEffect(shadow)
        self.outer.addWidget(self.shell)

        self.shell_layout = QVBoxLayout(self.shell)
        self.shell_layout.setContentsMargins(0, 0, 0, 0)
        self.shell_layout.setSpacing(0)
        self.titlebar = TitleBar(self, self.theme)
        self.shell_layout.addWidget(self.titlebar)
        self.content = AtmosphereSurface(self.theme)
        self.shell_layout.addWidget(self.content, 1)

        self.loading_timer = QTimer(self)
        self.loading_timer.setInterval(420)
        self.loading_timer.timeout.connect(self._animate_loading)
        self.loading_timer.start()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(5000)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start()

        self._build_content()
        self.refresh()

    # ----------------------------- structure / theme

    def _clear_layout(self, layout: QVBoxLayout | QHBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child = item.layout()
            if child is not None:
                self._clear_layout(child)  # type: ignore[arg-type]
            if widget is not None:
                widget.deleteLater()

    def _build_content(self) -> None:
        old_layout = self.content.layout()
        if old_layout is not None:
            self._clear_layout(old_layout)  # type: ignore[arg-type]
            old_layout.deleteLater()

        theme = self.theme
        self.shell.setStyleSheet(
            f"QFrame#shell {{ background: transparent; border: 1px solid {_css_rgba(theme.border_soft, 210)}; border-radius: 13px; }}"
        )
        self.titlebar.apply_theme(theme)
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(24, 9, 24, 14)
        layout.setSpacing(12)
        if isinstance(self.content, AtmosphereSurface):
            self.content.set_theme(theme)
        self.content.setStyleSheet("background: transparent;")

        layout.addLayout(self._top_tools())
        if theme.layout == "tech":
            self._build_tech(layout)
        elif theme.layout == "glass":
            self._build_glass(layout)
        elif theme.layout == "compact":
            self._build_compact(layout)
        else:
            self._build_minimal(layout)
        layout.addLayout(self._footer())
        self.setStyleSheet(
            "QWidget { font-family: 'Segoe UI', 'Inter', sans-serif; } QLabel { background-color: transparent; border: none; }"
        )
        # A child-level stylesheet (for example, text color) can override a
        # parent QLabel rule on some Qt platform plugins.  Appending the
        # transparent background here prevents black label rectangles both in
        # offscreen previews and on Windows with a translucent frameless shell.
        for label in self.content.findChildren(QLabel):
            label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            label.setAutoFillBackground(False)
            label.setStyleSheet(label.styleSheet() + " background-color: transparent; border: none;")
        self.refresh()

    def _top_tools(self) -> QHBoxLayout:
        t = self.theme
        row = QHBoxLayout()
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(8)
        brand = QLabel("ATTACK SHARK X11")
        brand.setStyleSheet(f"color: {t.text}; font-size: 11px; font-weight: 700; letter-spacing: 0.7px;")
        row.addWidget(brand)
        dot = QLabel("•")
        dot.setStyleSheet(f"color: {t.muted_2};")
        row.addWidget(dot)
        product = QLabel("Battery monitor")
        product.setStyleSheet(f"color: {t.muted}; font-size: 10px;")
        row.addWidget(product)
        row.addStretch()
        label = QLabel("Theme")
        label.setStyleSheet(f"color: {t.muted}; font-size: 10px;")
        row.addWidget(label)
        self.theme_combo = QComboBox()
        for key in THEME_ORDER:
            if key in THEMES:
                self.theme_combo.addItem(THEMES[key].name, key)
        index = self.theme_combo.findData(self.theme_key)
        self.theme_combo.setCurrentIndex(max(0, index))
        self.theme_combo.setFixedWidth(148)
        self.theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_combo.setStyleSheet(
            f"QComboBox {{ background: {t.surface_2}; color: {t.text}; border: 1px solid {t.border}; "
            "border-radius: 7px; padding: 6px 10px; font-size: 10px; font-weight: 600; }"
            f"QComboBox:hover {{ border-color: {t.accent}; }}"
            "QComboBox::drop-down { border: none; width: 24px; }"
            f"QComboBox QAbstractItemView {{ background: {t.surface_2}; color: {t.text}; border: 1px solid {t.border}; "
            f"selection-background-color: {t.accent}; selection-color: white; outline: none; }}"
        )
        self.theme_combo.currentIndexChanged.connect(self._theme_selected)
        row.addWidget(self.theme_combo)
        return row

    def _theme_selected(self, index: int) -> None:
        key = self.theme_combo.itemData(index)
        if (
            not key
            or key == self.theme_key
            or key not in THEMES
            or self._theme_switch_pending
        ):
            return
        # Rebuilding the widget tree inside QComboBox.currentIndexChanged can
        # invalidate the popup/event target on Windows.  Queue an atomic
        # surface replacement for the next event-loop turn instead.
        self._theme_switch_pending = True
        self.theme_combo.setEnabled(False)
        QTimer.singleShot(0, lambda selected=str(key): self._apply_theme_switch(selected))

    def _apply_theme_switch(self, key: str) -> None:
        if key not in THEMES:
            self._theme_switch_pending = False
            return
        old_content = self.content
        self.theme_key = key
        self.theme = THEMES[key]
        current = settings_load()
        current["theme"] = key
        settings_save(current)

        new_content = AtmosphereSurface(self.theme)
        self.content = new_content
        self.shell_layout.replaceWidget(old_content, new_content)
        old_content.hide()
        old_content.setParent(None)
        old_content.deleteLater()

        self._build_content()
        self._theme_switch_pending = False
        self.theme_changed.emit(self.theme_key)
        self.update()

    def _metric_cards(self, *, compact: bool = False) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12 if not compact else 10)
        self.status_card = StatCard(self.theme, "status", "STATUS", compact=compact)
        self.estimate_card = StatCard(self.theme, "clock", "ESTIMATE", compact=compact)
        self.rate_card = StatCard(self.theme, "rate", "RATE", compact=compact)
        for card in (self.status_card, self.estimate_card, self.rate_card):
            card.setFixedHeight(82 if not compact else 72)
            row.addWidget(card, 1)
        return row

    def _history_card(self, *, compact: bool = False) -> Card:
        t = self.theme
        card = Card(t, radius=10 if compact else 12)
        col = QVBoxLayout(card)
        col.setContentsMargins(17, 14, 17, 12)
        col.setSpacing(5)
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("Battery history")
        title.setStyleSheet(f"color: {t.text}; font-size: 14px; font-weight: 700;")
        sub = QLabel("Stored locally on this device")
        sub.setStyleSheet(f"color: {t.muted}; font-size: 9px;")
        titles.addWidget(title)
        titles.addWidget(sub)
        head.addLayout(titles)
        head.addStretch()
        self.range_selector = RangeSelector(t, self.range_secs)
        self.range_selector.changed.connect(self._range_changed)
        head.addWidget(self.range_selector)
        col.addLayout(head)
        self.chart = BatteryChart(t)
        if compact:
            self.chart.setMinimumHeight(225)
        col.addWidget(self.chart, 1)
        return card

    def _build_minimal(self, layout: QVBoxLayout) -> None:
        self.hero = HeroStrip(self.theme)
        layout.addWidget(self.hero)
        layout.addLayout(self._metric_cards())
        layout.addWidget(self._history_card(), 1)
        self.gauge = None
        self.status_title = self.status_subtitle = None

    def _build_tech(self, layout: QVBoxLayout) -> None:
        t = self.theme
        hero = Card(t, radius=10, glow=True)
        hero.setFixedHeight(128)
        row = QHBoxLayout(hero)
        row.setContentsMargins(18, 9, 18, 9)
        row.setSpacing(18)
        self.gauge = BatteryGauge(t, compact=True, show_caption=False)
        self.gauge.setFixedSize(126, 108)
        row.addWidget(self.gauge)
        status_col = QVBoxLayout()
        status_col.addStretch()
        status_row = QHBoxLayout()
        self.status_title = QLabel("Loading device...")
        self.status_dot = StatusDot(t.accent)
        status_row.addWidget(self.status_title)
        status_row.addWidget(self.status_dot)
        status_row.addStretch()
        status_col.addLayout(status_row)
        self.status_subtitle = QLabel("Checking mouse status")
        status_col.addWidget(self.status_subtitle)
        status_col.addStretch()
        row.addLayout(status_col, 1)
        badge = Card(t, alt=True, radius=8)
        badge.setFixedSize(126, 66)
        badge_col = QVBoxLayout(badge)
        badge_col.setContentsMargins(10, 8, 10, 8)
        b1 = QLabel("WIRELESS HID")
        b1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b1.setStyleSheet(f"color: {t.accent_2}; font-size: 9px; font-weight: 700;")
        b2 = QLabel("LIVE TELEMETRY")
        b2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b2.setStyleSheet(f"color: {t.muted}; font-size: 8px;")
        badge_col.addWidget(b1)
        badge_col.addWidget(b2)
        row.addWidget(badge)
        layout.addWidget(hero)
        layout.addLayout(self._metric_cards())
        layout.addWidget(self._history_card(), 1)
        self.hero = None
        self.status_title.setStyleSheet(f"color: {t.accent}; font-size: 18px; font-weight: 700;")
        self.status_subtitle.setStyleSheet(f"color: {t.muted}; font-size: 10px;")

    def _build_glass(self, layout: QVBoxLayout) -> None:
        t = self.theme
        body = QHBoxLayout()
        body.setSpacing(12)
        left = Card(t, alt=True, radius=16, glow=True)
        left.setFixedWidth(260)
        left_col = QVBoxLayout(left)
        left_col.setContentsMargins(18, 16, 18, 16)
        self.gauge = BatteryGauge(t, compact=False, show_caption=True)
        self.gauge.setFixedHeight(245)
        left_col.addWidget(self.gauge)
        self.status_title = QLabel("Loading device...")
        self.status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_title.setStyleSheet(f"color: {t.accent}; font-size: 16px; font-weight: 700;")
        self.status_subtitle = QLabel("Checking mouse status")
        self.status_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_subtitle.setWordWrap(True)
        self.status_subtitle.setStyleSheet(f"color: {t.muted}; font-size: 10px;")
        left_col.addWidget(self.status_subtitle)
        left_col.addStretch()
        profile = QLabel("ADAPTIVE GLASS PROFILE")
        profile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        profile.setStyleSheet(f"color: {t.accent_2}; font-size: 8px; letter-spacing: 0.8px;")
        left_col.addWidget(profile)
        body.addWidget(left)
        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(self._history_card(), 1)
        right.addLayout(self._metric_cards(compact=True))
        body.addLayout(right, 1)
        layout.addLayout(body, 1)
        self.hero = None
        self.status_dot = StatusDot(t.accent)

    def _build_compact(self, layout: QVBoxLayout) -> None:
        t = self.theme
        top = QHBoxLayout()
        top.setSpacing(10)
        battery = Card(t, radius=10)
        battery.setFixedHeight(108)
        battery.setMinimumWidth(310)
        battery_row = QHBoxLayout(battery)
        battery_row.setContentsMargins(13, 8, 14, 8)
        self.gauge = BatteryGauge(t, compact=True, show_caption=False)
        self.gauge.setFixedSize(102, 92)
        battery_row.addWidget(self.gauge)
        state_col = QVBoxLayout()
        state_col.addStretch()
        self.status_title = QLabel("Loading device...")
        self.status_subtitle = QLabel("Checking mouse status")
        self.status_subtitle.setWordWrap(True)
        state_col.addWidget(self.status_title)
        state_col.addWidget(self.status_subtitle)
        state_col.addStretch()
        battery_row.addLayout(state_col, 1)
        top.addWidget(battery, 1)
        self.estimate_card = StatCard(t, "clock", "ESTIMATE", compact=True)
        self.rate_card = StatCard(t, "rate", "RATE", compact=True)
        self.status_card = StatCard(t, "status", "STATUS", compact=True)
        for card in (self.estimate_card, self.rate_card, self.status_card):
            card.setFixedHeight(108)
            top.addWidget(card, 1)
        layout.addLayout(top)
        layout.addWidget(self._history_card(compact=True), 1)
        self.hero = None
        self.status_dot = StatusDot(t.accent)
        self.status_title.setStyleSheet(f"color: {t.accent}; font-size: 16px; font-weight: 700;")
        self.status_subtitle.setStyleSheet(f"color: {t.muted}; font-size: 10px;")

    def _footer(self) -> QHBoxLayout:
        t = self.theme
        row = QHBoxLayout()
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(9)
        self.startup_toggle = ToggleSwitch(t, startup_get())
        self.startup_toggle.toggled.connect(self._toggle_startup)
        row.addWidget(self.startup_toggle)
        startup = QLabel("Launch at Windows startup" if os.name == "nt" else "Launch at login")
        startup.setStyleSheet(f"color: {t.muted}; font-size: 9px;")
        row.addWidget(startup)
        row.addStretch()
        version = QLabel(f"v{__version__}")
        version.setStyleSheet(f"color: {t.muted_2}; font-size: 9px;")
        row.addWidget(version)
        for separator in (1,):
            pass
        sep1 = QLabel("•")
        sep1.setStyleSheet(f"color: {t.muted_2};")
        row.addWidget(sep1)
        self.update_link = ClickLabel("Check for updates")
        self.update_link.clicked.connect(self._check_updates)
        row.addWidget(self.update_link)
        sep2 = QLabel("•")
        sep2.setStyleSheet(f"color: {t.muted_2};")
        row.addWidget(sep2)
        repo = ClickLabel("★  Star on GitHub")
        repo.setStyleSheet(f"color: {t.muted}; font-size: 9px;")
        repo.clicked.connect(lambda: webbrowser.open(REPO_URL))
        row.addWidget(repo)
        self._style_update_link()
        return row

    # ----------------------------- state / interaction

    def _range_changed(self, value: Optional[int]) -> None:
        self.range_secs = value
        self.chart.set_data(self.controller.history_snapshot(), self.range_secs)

    def _toggle_startup(self, enabled: bool) -> None:
        try:
            startup_set(enabled)
        except Exception:
            self.startup_toggle.setChecked(startup_get())

    def _check_updates(self) -> None:
        update = getattr(self.controller, "update_info", None)
        if update is not None and getattr(update, "url", None):
            webbrowser.open(update.url)
        else:
            self.controller.start_update_check(force=True)

    def _style_update_link(self) -> None:
        if not hasattr(self, "update_link"):
            return
        checking = bool(getattr(self.controller, "update_checking", False))
        update = getattr(self.controller, "update_info", None)
        if checking:
            text, color = "Checking...", self.theme.muted
            self.update_link.setCursor(Qt.CursorShape.ArrowCursor)
        elif update is not None:
            text, color = f"Download v{update.version}", self.theme.accent_2
            self.update_link.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            text, color = "Check for updates", self.theme.muted
            self.update_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_link.setText(text)
        self.update_link.setStyleSheet(f"color: {color}; font-size: 9px;")

    def _state_text(self, mode: str, level: Optional[int]) -> tuple[str, str, str, str]:
        if mode == "loading":
            return "Loading device...", "Checking mouse status", "Waiting", "Waiting"
        if mode == "adapter" and level is not None:
            metrics = battery_metrics(self.controller.history_snapshot(), mode, level, time.time())
            label = state_label(mode, level, self.controller.threshold)
            subtitle = "Charge soon to avoid interruptions" if label == "Low battery" else (metrics.summary or "Battery level is healthy")
            return label, subtitle, metrics.estimate, metrics.rate
        if mode == "waiting":
            return "Connected", "Move the mouse to read the battery level", "Waiting", "Waiting"
        if mode == "charging":
            return "Charging", "Battery percentage is unavailable over USB", "Not available", "Not available"
        if mode == "error":
            return "Unavailable", "Unable to access the HID interface", "Not available", "Not available"
        return "Not connected", "Dongle not detected", "Not available", "Not available"

    def refresh(self) -> None:
        mode, level = self.controller.state_snapshot()
        status, subtitle, estimate, rate = self._state_text(mode, level)
        accent = status_accent(self.theme, mode, level, self.controller.threshold)

        if self._last_icon_state != (mode, level):
            self._last_icon_state = (mode, level)
            icon_pix = fin_pixmap(mode, level, 64)
            self.titlebar.set_icon(icon_pix)
            icon = QIcon(icon_pix)
            self.setWindowIcon(icon)
            if hasattr(self.controller, "set_window_icon"):
                self.controller.set_window_icon(icon)

        if getattr(self, "hero", None) is not None:
            self.hero.set_state(mode, level, self.controller.threshold, status, subtitle)
        if getattr(self, "gauge", None) is not None:
            self.gauge.set_state(mode, level, self.controller.threshold)
            if getattr(self, "status_title", None) is not None:
                self.status_title.setText(status)
                self.status_title.setStyleSheet(f"color: {accent.name()}; font-size: {'18' if self.theme.layout == 'tech' else '16'}px; font-weight: 700;")
            if getattr(self, "status_subtitle", None) is not None:
                self.status_subtitle.setText(subtitle)
            if hasattr(self, "status_dot"):
                self.status_dot.set_color(accent)

        self.status_card.set_value(status, "Device online" if status == "Connected" else "", accent)
        self.estimate_card.set_value(estimate, "remaining" if estimate not in ("Waiting", "Pending", "Learning", "Not available") else "")
        self.rate_card.set_value(rate, "average" if "%" in rate else "")
        self.chart.set_data(self.controller.history_snapshot(), self.range_secs)
        self._style_update_link()

    def _animate_loading(self) -> None:
        mode, _ = self.controller.state_snapshot()
        if mode != "loading":
            return
        dots = "." * (self._loading_frame % 3 + 1)
        self._loading_frame += 1
        text = f"Loading device{dots}"
        if getattr(self, "hero", None) is not None:
            self.hero.status.setText(text)
        elif getattr(self, "status_title", None) is not None:
            self.status_title.setText(text)

    def show_dashboard(self) -> None:
        self.show()
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        if os.name == "nt":
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            self.show()
            QTimer.singleShot(120, self._release_topmost)
        self.refresh()

    def _release_topmost(self) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_to_tray(self) -> None:
        self.hide()

    def closeEvent(self, event: Any) -> None:
        event.ignore()
        self.hide_to_tray()

    # Native edge resize for the custom title bar.
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        margin = 7
        pos = event.position()
        edges = Qt.Edge(0)
        if pos.x() <= margin:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= self.width() - margin:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= margin:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= self.height() - margin:
            edges |= Qt.Edge.BottomEdge
        self._resizing_edge = edges
        if edges in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edges in (Qt.Edge.TopEdge, Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edges in (
            Qt.Edge.LeftEdge | Qt.Edge.TopEdge,
            Qt.Edge.RightEdge | Qt.Edge.BottomEdge,
        ):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edges:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._resizing_edge:
            handle = self.windowHandle()
            if handle is not None and hasattr(handle, "startSystemResize"):
                handle.startSystemResize(self._resizing_edge)
        super().mousePressEvent(event)


class PreviewController:
    """Small controller used by the screenshot renderer and UI smoke tests."""

    threshold = 20
    update_info = None
    update_checking = False

    def __init__(self) -> None:
        now = int(time.time())
        self._state = ("adapter", 93)
        self._history = []
        for i in range(96):
            ts = now - (95 - i) * 900
            value = 100 - int(7 * i / 95)
            self._history.append((ts, value, "adapter"))

    def state_snapshot(self) -> tuple[str, Optional[int]]:
        return self._state

    def history_snapshot(self) -> list[tuple[int, Optional[int], str]]:
        return list(self._history)

    def start_update_check(self, *, force: bool) -> None:
        del force

    def set_window_icon(self, icon: QIcon) -> None:
        del icon


def render_theme_preview(theme_key: str, output: Path, size: tuple[int, int] = (1080, 720)) -> Path:
    """Render a real offscreen screenshot of a dashboard theme."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qt_app = QApplication.instance() or QApplication(sys.argv[:1])
    qt_app.setFont(QFont("Segoe UI", 10))
    window = DashboardWindow(PreviewController(), preview_theme=theme_key)
    window.resize(*size)
    window.show()
    qt_app.processEvents()
    QTimer.singleShot(80, qt_app.quit)
    qt_app.exec()
    pixmap = window.grab()
    output.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(str(output))
    window.close()
    return output
