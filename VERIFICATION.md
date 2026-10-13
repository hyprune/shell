# IPC 0.26 debug tool, companion pace, whole pocket list — 2026-10-13

`python3 -m unittest discover -s tests`: **363 pass**, including `tests/test_ipc26.py`
(11): the vendored 0.26 pin, no new grant or method, the Walk / Run requests built by
`qml/Companion.js` `paceParams` (kept mode; none on a route or without a companion)
against the 0.26 pin (refused by 0.25), `companionState.pace`, the `debugTool` shape,
tool 9 in `hud.pose` and the `tool9` world action, the HUD and tool-deck wiring for the
layer name and `LAYER n/N`, a 40-window pocket listed whole by Director > Surfaces, and
the dev status `surfaces` entry. `qmllint` on the changed QML: no errors. Nested with core
0.26 (`dev/nested/run.sh --windows`, this shell at 0.26): 22 pocketed room windows, all 22
listed in Director > Surfaces as "IN THE POCKET / 22"; `--debug-tool` with this shell: tool 9's
deck reads "DEBUG · LAYER 1/10" over "WINDOW BOXES & MOUNTS" (dev status `toolDeck`).

---

# IPC 0.25 companions (draft) — 2026-10-13

`python3 -m unittest discover -s tests`: **322 pass**, including `tests/test_ipc25.py`
(11): the vendored 0.25 pin, no new grant, the 0.25 allowlist (companion.set/clear/mode
only from 0.25), every companion request built by the shell and the results against the
0.25 pin (refused by 0.24), the companion state and catalog capability shapes, the
`qml/Companion.js` helpers (choices, status line, Follow/Stay) and the Settings >
Companion wiring. `qmllint` on `CompanionSettings.qml`: style hints only. Not yet captured
in a nested preview.

---

# RFC-0015 phase 1 Library tab — 2026-10-12

`python3 -m unittest discover -s tests`: **297 pass**, including `tests/test_library.py`
(20): the `qml/Library.js` helpers fed with the documents and JSON lines of the fake CLI
(`dev/fake-hyprune-cli.py`): contract fields of the listing documents, source labels and
licence wording, filters and search, card badges and actions, install rows and actions
(system-managed read only, pinned updates held), the Add source form (`https://` or
`github:`, label length, sha256 for a package URL), job arguments, plan provenance and
requirements, a source change that stays a confirmation until `--accept-source-change`,
errors with their rule, a CLI that can't start; plus source checks that the page uses plain
text only, opens no links, loads thumbnails only from local paths and never runs `--yes`
before the plan is confirmed. `./dev/run library` (nested, SDK mock and the fake CLI)
captures Browse, Installed and Sources at 1920×1080, 1280×720, 2560×1440 at scale 2 and
3840×2160, filters and search, the plan confirmation, the source change's second
confirmation, download progress, a finished library install refreshing the object catalog
and opening Objects, a hash mismatch with its rule, rollback / unpin / remove, adding and
refusing sources, disable / enable, and the HUD toast of a job finished with the Director
closed, with the layout audit clean and no QML runtime errors.

---

# IPC 0.23 characters, routes and interactions — 2026-10-12

`python3 -m unittest discover -s tests`: **277 pass**, including `tests/test_ipc23.py`
(34): 0.23 adds no grant, the 0.23 allowlist, every character, path and interaction request
built by the shell and every result against the 0.23 pin (and refused by 0.22), the npcs
state, 0.23 instance, editor path, reticle and graphics shapes, world format 0.9, the
bridge's choice-list input (exclusive overlay taken and released, Director and note prompt
keep theirs, core's Escape ends the interaction) and panel interaction, and the
`qml/Npcs.js` helpers. `./dev/run npcs` (nested, SDK mock with dev preview data) captures
the Catalog with character cards, the spawn step and the Characters view at 1920×1080,
1280×720, 2560×1440 at scale 2 and 3840×2160, the caption and aimed prompt at each size,
every spawn path (route with settings, Stand here by keyboard, stops saved, Draw a new
route), the drawing hint and bar (Done, Cancel), disable / enable, rebind, remove, the
motion setting, a paused reason, a refusal, the choice list driven by keys, guide and
waypoint toasts and panel interactions, with the layout audit clean and no QML runtime
errors. `./dev/run objects` still passes.

---

# IPC 0.22 object catalog and user placements — 2026-10-12

`python3 -m unittest discover -s tests`: **243 pass**, including `tests/test_ipc22.py`
(33): hello capabilities validate against every vendored pin (`objects.control` only from
0.22), the 0.22 allowlist, every object and library request built by the shell and every
result against the 0.22 pin (and refused by 0.21), error data rules reaching QML, the
`qml/Objects.js` helpers (catalog filters and search, card facts, grid cursor, configure
panel section order including the reserved Data slot, transform params, usage, toasts) and
object items in the tool 5 queue. `./dev/run objects` (nested, SDK mock with dev preview
data; `HYPRUNE_DEV_PREVIEW=nested` on a headless parent whose GPU can't allocate headless
buffers) captures the Catalog and Placed views at 1920×1080, 1280×720, 2560×1440 at scale 2
and 3840×2160 at scale 1 and 2 with the layout audit clean, filters and search, Add by
keyboard and button, every configure action, the confirm step, a refusal, the budget toast
and the tool 5 HUD in all three concepts, with no QML runtime errors.

---

# IPC 0.21 quests, focus sessions and guidance — 2026-10-12

`python3 -m unittest discover -s tests`: **207 pass**, including `tests/test_ipc21.py`
(30): hello capabilities validate against every vendored pin (`quest.control` only from
0.21), the 0.21 allowlist, request/result/state/event shapes against the 0.21 pin (and
refused by 0.20), event forwarding per session, the clock offset, and the `qml/Quests.js`
helpers (list grouping, form parsing and edit round trips, focus timing, toast routing and
queue, hold ring delay, guidance patches). `./dev/run quests` (nested, SDK mock with dev
preview data) captures the Quests page, form, Settings → Guidance, the HUD tracker, focus
chip, toasts and banner at 1920×1080, 1280×720 and 2560×1440 at scale 2, with the layout
audit clean, a keyboard check (arrows, T) and no QML runtime errors.

---

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

Reviewed video: `$HYPRUNE_VIDEO_DIR/hyprune-first-session.mp4`, **61.433333 s,
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
1920×1080 output; the host compositor is never controlled.

The UI was inspected using the screenshots and an extracted encoded-video frame.
Iterations corrected light-theme text contrast, Canvas initialization, smaller
output clipping and stale destination presentation. The graphics and orbital
seals are original Canvas/QML drawings; no prototype code or game assets ship.

## Review artifacts

Capture root: `$HYPRUNE_GALLERY_DIR` (environment or `~/.config/hyprune/dev.env`; unset: `dev/.run/gallery/`, with a warning).
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

Video: `$HYPRUNE_VIDEO_DIR/hyprune-shell-m0.mp4`, with adjacent
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

Concurrent 0.3 integration changes were developed separately and were not part
of these results. The recording above is the verified 0.2 result.

M3B IPC 0.6: `python3 -m unittest discover -s tests` passes 42 protocol,
lease, revision, reconnect and parser tests, including closed keymap/capture
requests, three-variant bounds and the Map opening intent. Real Settings capture/save, native
collision descriptions and HUD mode/submode are exercised by core's lifetime-
locked `dev/nested/run.sh --m3b` with the actual Quickshell Director.
