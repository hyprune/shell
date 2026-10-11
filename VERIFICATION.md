# First real session verification — 2026-10-07

Shell 0.2.0 runs with real core 0.2.0 in the locked nested harness over IPC 0.3.
The authoritative world map, seven places, output binding and screen projections
come from core; no presentation fixture or association/workspace emulator is used.
`../core/dev/hyprune-dev smoke` passes load/HUD output isolation, real walking,
core-owned Tab hold, credential-verified exclusive Director, Tab/Escape,
waypoint/route/autodrive, travel/warp, live station-anchored terminal/btop/Chromium,
actual pointer focus and typing, workspace warp out/back, rapid switching and exit
without a crash or QML runtime errors. The ordinary-window association forgery,
unassociated exclusivity and private PID spoof are rejected.

`python3 -m unittest discover -s tests -v`: **36/36 pass**, including IPC 0.3
method/version isolation. Core/schema/SDK suites and captured real wire traffic
are also green; see `../core/docs/FIRST-SESSION.md` and its evidence JSON.

Reviewed video: `videos/hyprune-first-session.mp4` in the gallery, **61.433333 s,
22,226,000 bytes**, H.264/yuv420p 1920×1080/30 fps with fast start, plus adjacent
metadata JSON. Full-resolution Map and extracted video frames were inspected;
btop displays live metrics and the Map waypoint is selected with a real pointer.
Every nested lifetime holds `flock /tmp/worldshell-nested.lock`; all control is
scoped to the verified child compositor. Cursor lifecycle stays unchanged.
Production supervisor renewal and dedicated DRM/hardware-cursor, full hotplug
and lock acceptance remain future work.

The historical M0/IPC 0.2 results below are preserved for that older profile.

---

# M0 verification — 2026-10-07

## Environment and contract pins

| Dependency | Tested version |
| --- | --- |
| Python / jsonschema | 3.14.7 / 4.26.0 |
| Node | 26.10.0 |
| Quickshell | 0.3.1, revision `41651d7` |
| Hyprland / Aquamarine | 0.56.2 / 0.15.1 |
| FFmpeg | 9.0.2 |
| SDK MockDaemon | `86c04ab` (unmodified SDK checkout) |
| IPC/world 0.1 schemas | `96dad32178b14d0c50f64413430d054133d40425` |
| Amended IPC/world 0.2 schemas | `c07a923`, exact source SHA-256 values in `protocol/v0.2/SOURCE.json` |

## Results

`python3 -m unittest discover -s tests -v`: **35 passing tests**. The connection
lifecycle tests run against separate frozen 0.1 and 0.2 validators. Coverage
includes fragmented multibyte/coalesced frames, bounded transport, duplicate keys,
invalid UTF-8/depth/nonfinite numbers, method-specific results, reversed replies,
atomic snapshot/first-delta ordering, gap resync, overlay reply/delta ordering,
fresh reconnect authority, no mutation replay, lock/unplug/revocation and competing
shell claims. Native 0.2 tests exercise lease/session-scoped UI events, pending
transition hints without baseline mutation, mid-jump snapshots, stable IDs, terminal reconnect suppression,
world/output-scoped indeterminate loading and failure, coalesced open/close,
stale-session hint discard and daemon revision reset.

`./dev/run capture`: actual SDK MockDaemon with exact IPC 0.2, all six views,
canonical waypoint/point travel, SDK-owned hold timing, native world loading,
workspace-to-world jump, light theme, reduced motion and confirmed arrival.
Nested-seat Right and Esc key presses assert navigation and dismissal. Forced
SDK disconnect/revocation assert fresh authenticated leases and a closed Director.
An explicit development association emulator enables the supervised QML child's
exclusive overlay; a separate adapter maps mock workspaces to native world.load.
Both are documented and excluded from production. No mock-only wire protocol is
used. Capture rejects QML/runtime errors and shuts down its child processes.
Each nested lifetime is wrapped in `flock /tmp/worldshell-nested.lock`.

`./dev/run core-check`: actual built plugin and `hypruned` at `4d53c2d`, with this
shell and no association emulator or presentation fixture. Native 0.2 handshake,
Tab hold, refused exclusive mapping, timed zone travel, passive warp/arrival,
indeterminate pending world loading and F12 during warp all pass. The isolated
harness normalizes the verified test-owned socket from 0700 to RFC 0600 and waits
300 ms for startup method advertisement. These core interop issues are recorded
in NOTES-rfc-gaps.md. Core build completed with no work required.

Earlier visible 1280×720 and headless 1080p runs verified composition scaling and
output selection. The latest captures and real-core run use the distinct nested
1920×1080 output; the owner's compositor is never controlled.

The UI was inspected using the screenshots and an extracted encoded-video frame.
Iterations corrected light-theme text contrast, Canvas initialization, smaller
output clipping and stale destination presentation. The graphics and orbital
seals are original Canvas/QML drawings; no prototype code or game assets ship.

## Review artifacts

Gallery root: `$HYPRUNE_GALLERY_DIR` (default `dev/.run/gallery/`).
Screenshots are **1920×1080**, stored under `screenshots/hyprune-shell-m0/`:

| View | File |
| --- | --- |
| Compass, minimap, objective, notices, marker samples, vehicle | `hud.png` |
| Director Map / selected waypoint | `map.png`, `map-waypoint.png` |
| Places / orbital destinations | `places.png` |
| Surfaces | `surfaces.png` |
| Workspaces | `workspaces.png` |
| Help / presentation preferences | `help.png` |
| What's new | `whats-new.png` |
| Paper theme | `map-light.png` |
| World jump | `warp-departure.png`, `warp-transit.png`, `warp-approach.png`, `warp-arrival.png` |
| Native point travel | `warp-point-travel.png` |
| Actual core HUD / warp | `native-core-hud.png`, `native-core-warp.png` |
| Workspace jump | `warp-workspace.png` |
| Reduced-motion destination card | `warp-reduced-motion.png` |
| Connection recovery | `reconnect.png` |

Video: `videos/hyprune-shell-m0.mp4`, with adjacent
`hyprune-shell-m0.json` (`title`, `tag`, `notes`). It shows the HUD, all six Director
views and the full jump/arrival sequence. The capture script asserts H.264,
`yuv420p`, 1920×1080, duration 20–40 seconds and size below 30 MB. The recording is
30.966667 seconds / 2,055,885 bytes; MP4 box order was inspected to verify `moov`
before `mdat` (`+faststart`). Sound remains disabled.

## Limits

The video uses real SDK 0.2 transport/events with explicit development association
and workspace mapping adapters. Projection, backdrop and speeder are presentation
fixtures; onboarding is shell-owned guidance. The schematic uses trusted manifest
hints because 0.2 has no authoritative map resource contract.

Core M1 rejects exclusive overlay input pending trusted Wayland-client association;
the real-core test confirms that the Director stays unmapped. Output mapping,
production token renewal, real lock handling, exclusive seat arbitration and
multi-monitor hotplug need further integration before full RFC-0008 conformance.
Workspace-to-location mapping remains development-only in this delivery. See
[NOTES-rfc-gaps.md](NOTES-rfc-gaps.md).

Concurrent 0.3 changes are owned by the integration agent and were not part of
these results. The gallery is the verified 0.2 recording.

M3B IPC 0.6: `python3 -m unittest discover -s tests` passes 42 protocol,
lease, revision, reconnect and parser tests, including closed keymap/capture
requests, three-variant bounds and the Map opening intent. Real Settings capture/save, native
collision descriptions and HUD mode/submode are exercised by core's lifetime-
locked `dev/nested/run.sh --m3b` with the actual Quickshell Director.
