# Changelog

## 1.1.1

- Fixed the Linux CI shutdown crash on Python 3.10 and 3.11 by selecting a compatible PySide6 release for those Python versions. Python 3.12 and newer continue to use the current PySide6 series.

## 1.1.0

- Added separate system notifications at 20%, 10%, and 5% battery, with each alert rearmed after the battery rises above its level.
- Fixed Linux wireless monitoring so it uses the hidraw backend and leaves the kernel mouse input driver attached; the pointer remains usable while the app is open.
- Added Linux HID diagnostics and udev rules for both hidraw and USB backends, including an installer for the rule.
- Improved the Linux installation instructions and made reinstalling update the app from the local checkout even when the version is unchanged.

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
