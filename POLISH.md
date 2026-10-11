# Shell polish — October 2026

The shell uses logical output dimensions instead of shrinking the Director to
half-sized text on 1080p/scale 2. Cards reflow, editorial and settings pages
scroll, headings have finite widths, and truncated labels expose full text on
hover. Settings separates appearance, graphics and input bindings; active
capture stays visible, with explicit cancellation and core-owned persistence.

HUD clusters rotate by up to 7.2° yaw / 4.2° pitch at the default strength.
`Tokens.hudCurved` and `Tokens.hudCurvature` control the effect. Settings offers
an off switch and strength slider. Qt Quick `Rotation` transforms operate on
the scene graph with no extra full-screen render texture or shader. The
Director and warp remain flat. Native input mapping uses Qt transforms; the
production HUD remains entirely pointer-transparent. World-locked markers
belong to core on 0.6/0.7 and are never bent by shell.

Reference: [Qt Quick Rotation](https://doc.qt.io/qt-6/qml-qtquick-rotation.html).
Small clusters use translucent dark scrims that composite over both bright
stone and dark interiors. HUD foreground colors are independent of the menu's
Paper/Night theme. Reveal timings share the reduced-motion-aware theme token.

Warp resolves known display names, retains learned world metadata and uses a
readable ID suffix only before a destination has been seen. Arrival updates to
the authoritative name. The same catalog populates Places and workspace homes.
Core does not yet advertise an installed-world catalog: Places lists worlds
learned this session (plus any trusted launcher manifests).

## Graphics handoff

Core's October 8 graphics work moved to exact IPC **0.7**, preserving 0.1–0.6.
Launch with `--protocol 0.7` to expose World graphics. Shell's offline validator
applies `core/docs/graphics-ipc-amendment.json` to the pinned 0.6 base; provenance
and amendment SHA-256 are in `protocol/v0.7/SOURCE.json`. Regenerate with
`python3 dev/sync-graphics-schema.py`. This is the core's explicit handoff;
canonical schema publication is tracked separately in the schema repository. Existing launchers
must opt into exact `--protocol 0.7` (or `HYPRUNE_PROTOCOL=0.7`) to expose
graphics; the default and older protocol contracts are not silently upgraded.

Settings renders advertised effect options, requested Preset/null values and
resolved values: quality, MSAA, bloom, fog, sky, reflections, normal maps,
specular, AO, transparent glass/haze, anisotropy and dynamic resolution, plus
render scale, target FPS, FOV, exposure, bloom strength, reconstruction sharpening and world reduced motion.
Unsupported screen-space reflections and runtime/contact shadows are described
without nonfunctional switches. Diagnostics poll at 1 Hz only while Settings
is visible. All changes use validated `graphics.set`; QML never writes files.

## Reproduction and evidence

All compositor control uses the child signature/Wayland socket or core's
PID/start-time/lock-verified `ctl.py`. The host Hyprland session is never targeted.
Run each independently (the mock and core scripts share the global lock):

```sh
python3 -m unittest discover -s tests -v
./dev/run polish
flock /tmp/worldshell-nested.lock python3 dev/polish-core.py
../core/dev/hyprune-dev smoke
# Current 1000 ms TAB hold with the legacy smoke assertions:
flock /tmp/worldshell-nested.lock python3 dev/polish-smoke.py
```

`dev/polish-core.py` uses core's nested session lifetime and a shell-owned
acceptance callback; it does not edit core sources. Graphics and input files
are isolated inside the test state directory. Settings capture uses real nested
seat events. Each frame also inspects visible text geometry for paint overflow.
The matrix covers 1920×1080, 2560×1440 and 3840×2160, each at output scale 1/2.
Includes long app/workspace titles and German-length world headings, both menu themes,
HUD flat/curved, bright Sun Court/dark Rime Vault, all Director pages and warp.

Before: `$HYPRUNE_GALLERY_DIR/screenshots/hyprune-shell-m0/`. Background
references were world-only captures.

After: `$HYPRUNE_GALLERY_DIR/screenshots/hyprune-shell-polish/`.
`mock-<height>p-s<scale>-*.png` and `core-<height>p-s<scale>-*.png` identify the
source and physical output scale. Compare `*-sun-court-flat.png` with
`*-sun-court-curved.png` at the same pose. Full run result is
`core-verification.json`. Video: `$HYPRUNE_VIDEO_DIR/hyprune-shell-polish.mp4` and
`.json`; recording and encoding happen in `/tmp` before the finished file is
moved into place.

## Core limitations

On IPC 0.7 and earlier TAB remains a static hint. On exact IPC 0.8 the ring
animates from core `keymap.holds` monotonic start/duration data. The bridge
computes remaining time, and QML animates locally. Removal, firing and disconnect
clear the ring; duration changes retain the original start. No shell keyboard
interception or per-frame progress IPC is used. Launch with `--protocol 0.8`
or `HYPRUNE_PROTOCOL=0.8`; an explicit older launcher argument stays older.

No automatic luminance sampling is exposed by core; scrims adapt by alpha
compositing with the world, with a stable dark floor for text contrast.

## Validation result

- 48 shell unit tests pass; Python harness compilation and `git diff --check` pass.
- SDK mock matrix passes all six output configurations: HUD flat/curved, all
  seven Director pages, Paper settings and warp; no QML runtime errors.
- Real core 0.7 matrix passes all six output configurations, including actual
  TAB/ESC, F8 capture and save, sparse graphics changes (including sharpen),
  all Director pages, both appearance themes and warp. No QML runtime errors.
- Screenshot inspection corrected fractional glyph overhang, compact capture
  visibility, missing clear icons and destination hierarchy. Geometry checks
  also reject truncated single-character icons. This is a finite fixture matrix,
  not a claim of testing every possible translation or font.
- Long native workspace/app/world names also pass at all six configurations;
  additional scrolled Places/Workspaces captures show cards and apps below the
  compact viewport. The run produced 201 PNGs.
- Video is 35.93 seconds, 1920×1080 H.264/yuv420p, with flat/curved comparison,
  Sun Court, Rime Vault and all seven flat Director pages.
- `hyprune-dev smoke` cannot pass unchanged: its 500 ms TAB hold is shorter than
  core's current 1000 ms threshold. `dev/polish-smoke.py` adapts only that hold
  while retaining every original assertion. It proceeds through movement,
  Director association, waypoint, autodrive and travel, then fails core's
  `dev/nested/integration.py:130` terminal-writing assertion: the marker exists
  but remains empty. Retrying with a settle delay produces the same result.
  This remains a core integration/input follow-up; no core source was edited.

Useful exact comparisons (under `$HYPRUNE_GALLERY_DIR/screenshots/`):

| View | Earlier baseline | Final capture |
| --- | --- | --- |
| HUD | `hyprune-shell-m0/hud.png` | `hyprune-shell-polish/core-1080p-s1-sun-court-curved.png` |
| HUD curvature off/on | `hyprune-shell-polish/core-1080p-s1-sun-court-flat.png` | `hyprune-shell-polish/core-1080p-s1-sun-court-curved.png` |
| Dark HUD | `hyprune-shell-m0/native-core-hud.png` | `hyprune-shell-polish/core-1080p-s1-rime-vault-curved.png` |
| Workspaces/apps | `hyprune-shell-m0/workspaces.png` | `hyprune-shell-polish/core-1080p-s2-long-workspaces-detail.png` |
| Places | `hyprune-shell-m0/places.png` | `hyprune-shell-polish/core-1080p-s2-places.png` |
| Warp | `hyprune-shell-m0/native-core-warp.png` | `hyprune-shell-polish/core-switchyard-arrival.png` |

Key capture: `hyprune-shell-polish/core-1080p-s2-settings-capture.png`.
Graphics: `hyprune-shell-polish/core-2160p-s1-settings-graphics.png` and
`core-2160p-s1-settings-graphics-detail.png`.

## Published-core follow-up

Core and schema were pulled before this follow-up. IPC 0.8 is pinned directly
from the published canonical schema; the existing 0.7 pin is byte-identical to
the published 0.7 file. Earlier statements about unpublished graphics schemas
and missing hold timing describe the initial polish run.

Workspace app rows now live inside their SurfaceCard, above the action button.
The card grows with the app list; titles and class names elide with tooltips.
The nested audit checks that app bounds lie within the containing card.

Reproduce the targeted acceptance independently under the shared lock:

```sh
flock /tmp/worldshell-nested.lock python3 dev/followup-core.py
HYPRUNE_FOLLOWUP_PROTOCOL=0.7 flock /tmp/worldshell-nested.lock python3 dev/followup-core.py
```

The harness uses real nested keyboard events on the Settings ComboBoxes to
select Ultra and Bloom Off. It then checks independent `graphics.get`, renderer
configuration, persisted settings, and F3 before/after captures. IPC 0.8 also
checks increasing rendered HoldRing progress, early-release cancellation, and
hold completion opening the Director. This last check currently exposes the core
version-gate blocker below. Workspace captures cover 1080p/scale 2,
1440p/scale 1 and 4K/scale 2 with long titles and native workspace names.

Evidence: `$HYPRUNE_GALLERY_DIR/screenshots/hyprune-shell-followup/`, including
`graphics-0.7-before-f3.png`, `graphics-0.7-after-f3.png`,
`hold-08-progress.png`, `workspaces-0.7-1440p-s1.png` and per-protocol
`verification-0.7.json` / `verification-0.8.json`.
The old app-below-card comparison is
`hyprune-shell-polish/core-1440p-s1-long-workspaces.png`.

Follow-up results: 50 shell unit tests pass. The 0.7 nested acceptance passes,
including real dropdown input, renderer/persistence checks and app containment.
On 0.8, increasing rendered ring progress and early-release clearing pass, but
Director opening is blocked by `core/src/platform/hyprland/Plugin.cpp:2721`:
its `shell.overlay` exclusive-input version allowlist ends at 0.7. Core returns
`-32007: verified association requires IPC 0.3` for the authenticated 0.8 shell.
The shell keeps this failure visible and does not bypass exclusive-input checks.
The 0.8 acceptance intentionally fails until core adds 0.8 to that allowlist.
Do not switch the normal launcher to 0.8 until core resolves it. No core source
was edited; all runs used the nested lock and isolated test configuration.
