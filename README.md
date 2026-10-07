# Hyprune shell

An original Quickshell HUD and Director for a world-driven desktop. The compass,
map, objective, notice, vehicle and orbital-navigation ideas draw on the owner's
prototype; code, component structure and Canvas graphics are original.

**IPC 0.2 is the default.** The shell uses canonical `ui.opened` / `ui.closed`,
`waypoint.set` / `travel.start`, seven-key revisioned state, and native
`location.transition` loading/travel events. Exact 0.1 is an explicit compatibility
option. No `0.1-mock.1`, `world.metadata` channel or notice-carried warp remains.

Core M1 still refuses exclusive input without a verified Wayland-client
association. The shell respects that refusal and leaves its Director unmapped.
The visual dev loop explicitly emulates this missing association for its
supervised QML child; it does not enable a production bypass. Real-core passive
HUD/warp, hold timing, loading and emergency escape have separate integration
checks. See [NOTES-rfc-gaps.md](NOTES-rfc-gaps.md).

## Development loop

Requires Python 3.11+, jsonschema 4.x, Node 22.12+, Quickshell, Hyprland 0.56 with
Lua configuration, `flock`, `hyprctl`, `grim` and `wtype`. Recording uses
`wf-recorder`, `ffmpeg` and `ffprobe`. Build the sibling SDK 0.2 checkout first:

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

Two current core startup issues require documented test setup: its bind creates
an owned 0700 socket, which this verified harness changes to the RFC's 0600, and
method advertisement arrives shortly after the socket becomes visible. The
harness allows startup to settle before consuming a launch token. The production
bridge continues requiring 0600 and honoring the actual hello profile.
`HYPRUNE_CORE_DIR` selects another core checkout. Results/logs stay in ignored
`dev/.run/core/`.

## Director and HUD

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
| `bridge/protocol.py` | Pinned 0.1 / 0.2 offline validation and framing |
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
