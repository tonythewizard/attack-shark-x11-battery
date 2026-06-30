# Changelog

## 1.0.0

- Fixed live theme switching on Windows by replacing the dashboard surface atomically on the next Qt event-loop turn; changing theme no longer leaves a blank or frozen window.
- Fixed compact and tech gauge clipping by keeping the full antialiased stroke and glow inside each gauge widget at every supported window size.
- Added a translucent, theme-aware atmospheric background with layered glows, ribbons, subtle texture, and distinct visual geometry for each theme.
- Made dashboard cards partially translucent so the new background remains visible while preserving contrast.
- Replaced the Tkinter dashboard and pystray integration with a native PySide6/Qt interface and `QSystemTrayIcon`.
- Rebuilt all four themes as real Qt layouts with antialiased gauges, gradients, rounded cards, high-DPI rendering, and custom chart painting.
- Added native tray double-click handling that opens or focuses the existing dashboard.
- Added real offscreen screenshot generation and Qt smoke tests for every theme.
- Added four persistent dashboard themes: Minimal Dark, Tech Blue, Modern Glass, and Compact Pro, with a selector in the upper-right corner.
- Added native tray activation: double-clicking the tray icon opens or focuses the dashboard without making the Dashboard menu item bold.

- Simplified the tray menu: the live battery entry and Dashboard are now normal clickable items, while update checks live in the dashboard footer.

- Replaced ambiguous `Calculating` telemetry placeholders with `Learning`, `Monitoring`, `Pending`, and `Stable` states.

- Fixed transient HID interface failures causing the dashboard to fall back to the loading/waiting state after briefly showing the battery percentage.

- Polished dashboard with compact telemetry cards and an improved history chart.
- Animated `Loading device...` state instead of placeholder dashes.
- Neutral `Connected` state replaces `Discharging`.
- Dynamic fin icon in the tray, dashboard header, title bar, and taskbar window.
- Single-instance behavior: launching the app again opens the existing dashboard.
- Automatic GitHub Releases update checks.
- Native Windows installer build using PyInstaller and Inno Setup.
- Linux source installation files retained in the repository.
