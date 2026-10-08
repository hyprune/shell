# Hyprune shell

Quickshell HUD and Director for a world-driven desktop. Shell 0.2.0 supports exact
IPC 0.1–0.6. The first real session runs against core through the
locked `../core/dev/hyprune-dev up|smoke|record` launcher. Core supplies the current
world metadata, safe SVG map, places, output descriptor, projected markers and
workspace locations. No launcher package paths are needed for that session.

Hold Tab in exploration to open the Director; core owns the configurable 1000 ms hold in M3B. The
bridge binds its direct Quickshell child, core verifies the actual Wayland HUD
credentials, and the Director maps only after exclusive overlay acceptance.
Escape closes it; F12 returns to the desktop. HUD/warp remain passive and only
on the world monitor. Map supports waypoint, travel and collision-checked
autodrive. Workspaces opens the mapped location using core's loading lifecycle.

Older protocols and the development mock retain their explicit limits below.
The real showcase and verification are documented in
[VERIFICATION.md](VERIFICATION.md).

## Development loop

Requires Python 3.11+, jsonschema 4.x, Node 22.12+, Quickshell, Hyprland 0.56 with
Lua configuration, `flock`, `hyprctl`, `grim` and `wtype`. Recording uses
`wf-recorder`, `ffmpeg` and `ffprobe`. Build the sibling SDK checkout first:

```sh
# Once in ../sdk:
npm ci
npm run build

# In this repository:
python3 -m pip install -r requirements.txt
./dev/run
```

This launches the SDK's actual IPC 0.2 `MockDaemon` with
[dev/scenario.json](dev/scenario.json), plus this shell in a visible nested Wayland
window. `preview` is an alias. The SDK owns the 350 ms hold timer; a supervisor
trigger feeds its `hold` API and the shell receives `ui.opened`. Ctrl+C stops the
run. `HYPRUNE_SDK_DIR` selects another checkout; the tested pin and adapter hooks
are recorded in `dev/SDK-SOURCE.json`.

```sh
./dev/run tour          # six views, then a native world load
./dev/run strict        # faithful SDK behavior; exclusive Director unsupported
./dev/run check         # IPC 0.2 + 1080p visual smoke check
./dev/run check-window  # visible 1280x720 composition check
./dev/run capture       # screenshots, 20–40 s video and recovery checks
HYPRUNE_SKIP_RECORD=1 ./dev/run capture
python3 -m unittest discover -s tests -v
```

Every nested lifetime is wrapped in `flock /tmp/worldshell-nested.lock`. The
harness reads the child compositor's startup environment, rejects the outer
signature/display, gives every `hyprctl` call an explicit child signature and
`qs ipc` its exact child PID. It never controls the owner's session. Interactive
runs use the visible nested output; deterministic captures use the distinct
1920×1080 `HYPRUNE-PREVIEW` output.

The SDK intentionally mirrors core's unsupported exclusive-input error. The
**development association emulator** intercepts only accepted `shell.overlay`
intent for the authenticated shell, verifies the supervised Quickshell child is
alive, checks connection-owned leases, and commits the schema-valid overlay.
A second test adapter maps mock workspace focus to native `world.load` using
[dev/workspace-locations.json](dev/workspace-locations.json). Neither adds wire
methods/events or modifies SDK files. Both remain excluded from production.
`strict` disables these adapters.

## Real-core check

Build core and generate its fixtures per `../core/README.md`, then:

```sh
./dev/run core-check
```

This starts another isolated nested compositor and the actual built plugin /
`hypruned`, with memory-only launch grants. Its controller checks PID/start time,
config, lock identity and child Wayland display before every control command.
It verifies native 0.2 hold timing, exclusive refusal, timed travel, passive warp,
arrival, pending world loading and F12 during a jump. No association emulator or
presentation fixture is supplied to this shell.

Historical M1 core startup issues required documented test setup: its bind creates
an owned 0700 socket, which this verified harness changes to the RFC's 0600, and
method advertisement arrives shortly after the socket becomes visible. The
harness allows startup to settle before consuming a launch token. The integrated core now creates a 0600 socket itself. The production
bridge continues requiring 0600 and honoring the actual hello profile.
`HYPRUNE_CORE_DIR` selects another core checkout. Results/logs stay in ignored
`dev/.run/core/`.

## Director and HUD (legacy development loop)

The HUD shows a compass, shared schematic minimap, zone-entered titles, notices,
and core-owned input hints on the leased world monitor only. Pose/heading and
explicit projected samples use separate bounded 70 ms interpolation buffers.
Reduced motion bypasses interpolation. Projection, vehicle and backdrop are
explicit dev fixtures; the onboarding checklist is shell-owned guidance, not a
world quest API.

- **Map:** trusted launcher manifest spawns, hover cards, click to set a waypoint,
  double click to `travel.start`, and an explicit arrive/reload at spawn action.
  M1 Target coordinates are eye positions; manifest spawns place capsule feet,
  so spawn targets use M1's documented-in-core 1.7 m eye offset. A future contract
  should provide a resolved spawn Target rather than requiring that convention.
- **Places:** orbital seals, destinations and native world loading.
- **Surfaces / Workspaces:** state descriptors and explicit `surface.focus` intent.
  Unsupported/hidden-workspace operations remain core decisions. Workspace travel
  mapping exists only in the named development adapter.
- **Help:** input routing, desktop escape, movement mode, theme, reduced motion,
  and optional warp sound.
- **What's new:** the original interface and current milestone.

Tab moves focus, Left/Right changes view, Esc dismisses via `ui.close`, and the
keyboard-accessible **Return to desktop** button invokes `runtime.exit`.
Core's independent F12 escape remains available even without shell or daemon.
The Director maps only after accepted `shell.overlay` exclusivity. HUD and warp
layers have empty pointer regions and no keyboard focus.

## Warp

Core and SDK native transition IDs, leased output, phase, progress, destination
and session/revision drive the overlay. Valid loading hints can present while a
world-load RPC is pending without modifying the state baseline. Arrival waits
for the matching committed state revision and destination world. Revision gaps
suppress hints until resync; reconnect resumes in-flight state and never replays
terminal snapshots.

World loading shows an indeterminate card, accelerating streaks and **LOADING**.
Point/zone travel shows actual core progress with eased presentation and an
approach deceleration. Failure, cancellation, exit, lease loss or disconnect clear
the overlay. Reduced motion uses a static card; point travel requests zero duration.
Sound is off by default. Optionally set `HYPRUNE_WARP_SOUND` to an original local
audio file and enable it in Help; `pw-play` plays once on the world output.

The scenario gives mock worlds a 5.8 s native load delay. The shell invents no
loading percentage or readiness. No file polling drives presentation.

## IPC bridge and trusted launch

`bridge/launch.py` supervises Quickshell and a private 0600 newline-JSON socket in
a 0700 runtime directory. QML uses `Quickshell.Io.Socket`; the Python helper owns
the separate binary core connection. A helper handles four-byte big-endian
framing, UTF-8 byte lengths, partial reads, bounded transport, SO_PEERCRED and
pinned offline schemas outside the UI loop. Node SDK modules cannot be imported
into QML. This helper is shell transport, not another core daemon.

A trusted supervisor provides a new one-use token on `HYPRUNE_TOKEN_FD`, never
credential text in argv, QML, logs or files. Ratified `HYPRUNE_SOCKET`,
`HYPRUNE_PROTOCOL` and `HYPRUNE_CLIENT_ID` are supported, with explicit overrides:

```sh
python3 bridge/launch.py \
  --protocol 0.2 --client-id com.hyprune.shell \
  --output opaque-core-output=DP-1 \
  --world-package /approved/package/world.json
```

The default socket is
`$XDG_RUNTIME_DIR/hyprune/$HYPRLAND_INSTANCE_SIGNATURE/control.sock`.
Unset/unsafe instance names are refused; there is no `/tmp` fallback. Output
bindings are trusted hints intersected with runtime membership and actual screens.
The shell requests the six shell grants, honors returned methods/capabilities,
and does not request `data.publish`. Integration state remains revisioned.

Reconnect obtains a new token, snapshot/subscription and leases; mutations are
never replayed. Responses match request IDs and method-specific result schemas.
Delta gaps suspend replacement application and request an atomic snapshot.
Transient events with old sessions/revisions are discarded. UI request generations
prevent coalesced open/close events or late replies from reopening a dismissed UI.

The local mock supervisor renews tokens over duplex FD 3 (`renew\n` -> token line).
This reissue convention remains development-only; a one-shot FD supports initial
authentication, while production renewal needs a supervisor contract.

## Fork the presentation

| Path | Responsibility |
| --- | --- |
| `bridge/protocol.py` | Pinned 0.1 / 0.2 / 0.3 offline validation and framing |
| `bridge/client.py` | Session, grants, state revisions, leases and native presentation |
| `bridge/launch.py` | Token FD, supervised UI and private presentation socket |
| `qml/ShellState.qml` | Presentation store, interpolation and arrival gating |
| `qml/theme/Tokens.qml` | Colors, fonts, spacing, motion and sound preference |
| `qml/components/Director*.qml` | One component per Director view |
| `qml/components/MapView.qml` | Shared schematic/minimap and interactions |
| `qml/components/Hud.qml` | HUD, onboarding, notices, prompts and dev vehicle |
| `qml/components/Warp.qml` | Passive transition graphics |
| `Seal.qml`, `Constellation.qml`, `Reveal.qml` | Original graphics and reveal motion |
| `dev/` | Locked SDK/core harnesses, scenarios and review capture |

Alternative shells can reuse protocol behavior without importing this look.
Manifest hints are approved reads once, not filesystem discovery. M0 preferences
are session-local. No executable extension, world art/physics, compositor hook,
or invented approval API is shipped here.

See [VERIFICATION.md](VERIFICATION.md) for results and gallery paths,
[NOTES-rfc-gaps.md](NOTES-rfc-gaps.md) for deferred contracts and core interop issues.
Schema provenance is in `protocol/SOURCE.json` and `protocol/v0.2/SOURCE.json`.
MIT; vendored schemas retain their license. All shell graphics are original.

Core M2 additionally negotiates IPC 0.4. The reference Director shows bound
workspace homes through `workspaces.locations`, and offers Pull out, Place at
home, Return and Recall all windows when those methods are advertised. Mount
ownership and restored placement state are authoritative in `mounts`; these
actions are unavailable on older negotiated protocols. The pinned 0.4 schemas
are in `protocol/v0.4/`. Core owns focus, collision recovery and persistence.

## M3A hands-on desktop

IPC 0.5 adds the authoritative movement/typing/workspace/fullscreen mode, noclip,
selected tool and five slots to the HUD. The Workspaces tab lists each workspace's
open app icon, title and class. Icons resolve through the local theme. Launch with
`python3 bridge/launch.py --protocol 0.5`; `protocol/v0.5/` pins the exact schema.
Core owns gestures, cursor/input routing, fullscreen, flight and placement. See
`../core/docs/M3A.md` for controls, config and supervised hardware cursor testing.
Older versions retain their existing mode-independent presentation.

M3B uses exact IPC 0.6 (`python3 bridge/launch.py --protocol 0.6`). The Director’s
Settings tab lists every mode/action with three capture boxes, clear controls,
conflicts, native shortcut stealing, long-hold timing and scope vignette. Save
uses core `input.set` with `input.control`; shell never writes the input file.
HUD shows world/interactive/focus/menu and the selected tool/submode. TAB hold
opens Map. Super+Tab or Back leaves E/F; Esc closes the Director. Defaults and
option ranges are generated in the docs site's Keymap page, with HJKL first.
