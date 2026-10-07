# M0 verification — 2026-10-07

## Environment and contract pins

| Dependency | Tested version |
| --- | --- |
| Python / jsonschema | 3.14.7 / 4.26.0 |
| Node | 26.10.0 |
| Quickshell | 0.3.1, revision `41651d7` |
| Hyprland / Aquamarine | 0.56.2 / 0.15.1 |
| FFmpeg | 9.0.2 |
| SDK MockDaemon | `3ab86cb` (unmodified SDK checkout) |
| IPC/world 0.1 schemas | `96dad32178b14d0c50f64413430d054133d40425` |
| Amended IPC/world 0.2 schemas | `c07a923`, exact source SHA-256 values in `protocol/v0.2/SOURCE.json` |

## Results

`python3 -m unittest discover -s tests -v`: **33 passing tests**. The connection
lifecycle tests run against separate frozen 0.1 and 0.2 validators. Coverage
includes fragmented multibyte/coalesced frames, bounded transport, duplicate keys,
invalid UTF-8/depth/nonfinite numbers, method-specific results, reversed replies,
atomic snapshot/first-delta ordering, gap resync, overlay reply/delta ordering,
fresh reconnect authority, no mutation replay, lock/unplug/revocation and competing
shell claims. Native 0.2 tests exercise lease/session-scoped UI events, future
transition hints, mid-jump snapshots, stable IDs, terminal reconnect suppression,
world/output-scoped indeterminate loading and failure.

`./dev/run check` and `./dev/run check-window`: strict SDK 0.1 handshake, atomic
state and output lease with the real Quickshell project. The visible 1280×720
Director was inspected and corrected to scale its 1080p composition without
clipping. The 1080p capture output is distinct from the visible nested output.

`./dev/run capture`: actual SDK MockDaemon with opt-in `0.1-mock.1`, all six views,
waypoint / preview travel, daemon-requested Director opening, world jump,
workspace-to-world jump, light theme, reduced motion and arrival. Nested-seat
Right and Esc key presses assert view navigation and dismissal. Forced SDK
disconnect/revocation assert fresh authenticated leases and a closed Director.
Capture rejects QML/runtime error messages. Child processes shut down after the
run; each nested lifetime is wrapped in `flock /tmp/worldshell-nested.lock`.

The UI was inspected using the screenshots and an extracted encoded-video frame.
Iterations corrected light-theme text contrast, Canvas initialization, smaller
output clipping and stale destination presentation. The graphics and orbital
seals are original Canvas/QML drawings; no prototype code or game assets ship.

## Review artifacts

Gallery root: `/home/user/hyprune-gallery`.
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
| Workspace jump | `warp-workspace.png` |
| Reduced-motion destination card | `warp-reduced-motion.png` |
| Connection recovery | `reconnect.png` |

Video: `videos/hyprune-shell-m0.mp4`, with adjacent
`hyprune-shell-m0.json` (`title`, `tag`, `notes`). It shows the HUD, all six Director
views and the full jump/arrival sequence. The capture script asserts H.264,
`yuv420p`, 1920×1080, duration 20–40 seconds and size below 30 MB. The recording is
32.4 seconds / 2,085,602 bytes; MP4 box order was inspected to verify `moov`
before `mdat` (`+faststart`). Sound remains disabled.

## Limits

The video uses real SDK transport and methods, with an explicitly named local
loading scenario adapter. The backdrop, projected samples, speeder and objective
checklist are development presentation fixtures. The schematic comes from trusted
launcher manifest hints; no authoritative map asset is available in the contract.

Native 0.2 was validated with schema-backed socket tests, **not this shell against
real core**. Core M1 rejects exclusive overlay input pending trusted Wayland-client
association. The production supervisor/output mapping, real lock/escape/seat
arbitration and multi-monitor hotplug need integration tests before full RFC-0008
conformance can be claimed. Workspace-to-location mapping remains preview-only.
See [NOTES-rfc-gaps.md](NOTES-rfc-gaps.md).
