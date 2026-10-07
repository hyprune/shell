# Hyprune shell

An original Quickshell HUD and Director for a world-driven desktop. M0 brings the
prototype's compass, map, projected-marker, objective, notice, vehicle and orbital
navigation ideas into small components. Original Canvas graphics replace game
iconography; no prototype code or external game assets are shipped.

The shell negotiates **exact IPC `0.1` by default**. It consumes atomic snapshots
and replacement deltas, claims one explicitly mapped world output, and maps the
interactive Director only after core accepts `shell.overlay`. HUD and warp layers
have empty pointer regions and no keyboard focus. Core retains input authority.

M0 is a working shell/client and visual preview, **not a claim of complete
RFC-0008 conformance with today's core**. Production `--protocol 0.2` opts into
the new native `ui.opened`/`ui.closed`, waypoint/travel and revisioned location
transition contract. Core M1 still refuses exclusive input until a verified
Wayland-client association exists. Output mapping, projection and map/catalog
delivery also remain gaps. The independently pinned SDK `0.1-mock.1` preview
demonstrates the complete interactive UI; it is the protocol used in the video.
See [NOTES-rfc-gaps.md](NOTES-rfc-gaps.md) for the exact boundary.

## Run the development loop

Requires Python 3.11+, `jsonschema` 4.x, Quickshell, Hyprland 0.56 with its Lua
configuration API, Node 22.12+, `flock`, `hyprctl`, `grim`, and `wtype`. Recording also
uses `wf-recorder`, `ffmpeg` and `ffprobe`. Build the independently checked out SDK:

```sh
# Once, in ../sdk:
npm ci
npm run build

# In this repository (use a virtualenv if jsonschema is not installed):
python3 -m pip install -r requirements.txt
./dev/run preview
```

`./dev/run` starts strict `0.1`; `preview` opts into `0.1-mock.1`. Both start the
SDK's actual `MockDaemon` with [dev/scenario.json](dev/scenario.json) and this shell
in a visible nested Wayland window. The Director opens once through the diagnostic
launcher trigger. `tour` walks the six tabs then jumps to the garden. Ctrl+C stops
the whole nested run. Override the sibling SDK checkout with `HYPRUNE_SDK_DIR`.

Every run is wrapped for its **entire lifetime** in
`flock /tmp/worldshell-nested.lock`. The harness reads the child compositor's own
startup environment, rejects the outer signature/display, and gives every
`hyprctl` call the explicit child signature and every `qs ipc` call the exact child
PID. It never queries, changes, or sends commands to the owner's compositor.
The headless 1920×1080 `HYPRUNE-PREVIEW` output is used only for captures/checks;
interactive runs show the world UI on the visible nested output instead.

```sh
python3 -m unittest discover -s tests -v
./dev/run check                     # strict wire + 1080p Director smoke check
./dev/run check-window              # visible nested-output layout check
./dev/run capture                   # screenshots, 32 s video and recovery checks
HYPRUNE_SKIP_RECORD=1 ./dev/run capture  # screenshot/recovery iteration
```

Capture artifacts default to
`~/hyprune-gallery/screenshots/hyprune-shell-m0/`
and `.../videos/hyprune-shell-m0.mp4` with its `.json` metadata.
`HYPRUNE_GALLERY_DIR` overrides that gallery root. Transient logs and recording
intermediates stay in ignored `dev/.run/`. No file polling drives shell state.

## Director and warp

- **Map:** original schematic generated around launcher-supplied RFC-0004 spawn
  positions, hover cards, waypoint click and travel double click when advertised.
  Native `0.2` calls `travel.start`; mock preview uses `camera.set`. Strict `0.1`
  disables these intents and offers `world.load` at spawn.
- **Places:** orbital destination seals, selection and world loading through IPC.
- **Surfaces / Workspaces:** live state descriptors and explicit keyboard-focus
  requests. Unsupported/hidden-workspace operations remain core decisions.
- **Help:** input routing, desktop escape, movement mode, light/dark presentation,
  reduced motion and optional warp sound.
- **What's new:** the M0 changes and the preview's limitations.

Tab moves focus, Left/Right changes view, and Esc unmaps the Director and releases
exclusivity. A visible, keyboard-accessible **Return to desktop** button invokes
`runtime.exit`; it does not terminate the compositor. Core's independent emergency
binding must remain available even when no shell or daemon is alive.

[dev/warp-scenario.json](dev/warp-scenario.json) stages departing, transit, approach
and arrival over 5.8 seconds. A mock-daemon decorator delays activation and emits
schema-valid `runtime.notice` frames with the dev-only code
`dev.location.transition`. The preview bridge validates the JSON message against
its local presentation schema. This is an explicit development adapter, **not an
additional IPC `0.1` event**. Only a new negotiated protocol can introduce the
proposed production `location.transition` event.

Mock world travel and workspace focus that maps to another world use the same jump
scenario. The warp closes the Director, shows accelerating star streaks with
layered soft/chromatic edges, destination text and authoritative progress, then
waits for the destination in the state stream before declaring arrival. Disconnect,
revocation, exit and failure clear it. Reduced motion uses a static destination
card with progress. Sound is off by default: optionally set `HYPRUNE_WARP_SOUND`
to an original local audio file and enable it in Help (`pw-play` is the hook).

Native `0.2` reads `location.transition` from committed snapshots/deltas and treats
transient events as hints tied to session/revision. It uses core's stable operation
ID and matching output, shows indeterminate loading without a percentage, and
handles world destinations, point/zone travel, cancellation and failure. A join
mid-jump resumes its presentation; terminal reconnect snapshots do not replay it.
Arrival waits for the matching committed revision and destination world. Zone
banners use authoritative pose against supplied zone bounds. Native 0.2 is covered
by schema-backed wire tests; real-core interactive integration is still pending.

## IPC bridge and trusted launch

`bridge/launch.py` starts Quickshell and a private 0600 presentation socket in a
0700 directory beneath `XDG_RUNTIME_DIR`. QML uses `Quickshell.Io.Socket` with
newline JSON; the Python bridge owns the separate binary core connection.
Quickshell's socket API reads/writes strings, so a helper keeps the four-byte
big-endian prefix, UTF-8 byte lengths, partial reads, malformed transport checks,
SO_PEERCRED and offline schema validation out of QML's UI loop. The SDK's Node
client cannot be imported into QML; no second core daemon is created.

`HYPRUNE_SOCKET` / `--socket` can select the public socket; otherwise it defaults to
`$XDG_RUNTIME_DIR/hyprune/$HYPRLAND_INSTANCE_SIGNATURE/control.sock`.
Unsafe/unset instance names are refused. There is no `/tmp` fallback. A trusted
supervisor launches the bridge with a fresh one-shot token on `HYPRUNE_TOKEN_FD`
(or `--token-fd`), never token text in argv, QML, logs or a file. Labels and package
hints are supplied explicitly, for example:

```sh
# The supervisor provides the token FD and the actual world output identity.
python3 bridge/launch.py \
  --protocol 0.2 \
  --output opaque-core-output=DP-1 \
  --world-package /approved/package/world.json
```

`HYPRUNE_PROTOCOL` can also choose the exact production version; no automatic
upgrade occurs. The bridge requests the six shell grants and honors the returned subset and
methods/events. Reconnect uses a new token, a fresh subscription/snapshot and new
leases. Mutations are never replayed. Delta gaps suspend application until an
atomic snapshot response resets the baseline. Responses match both request IDs
and their method result schema, including replies that precede coalesced state.

The local development supervisor wraps the SDK's mock API and renews one token
per connection over duplex FD 3 (`renew\n` -> token line). This private launcher
convention is not ratified by the RFC. The SDK CLI's single-use FD also works for
the first connection; authenticated reconnect requires a renewing supervisor.
The `--mock-preview` flag requires an explicit `--presentation` fixture; it is
never silently negotiated with production core. Native `ui.close` dismisses 0.2
panels; mapping still requires accepted `shell.overlay` exclusivity.

## Fork the presentation

| Path | Responsibility |
| --- | --- |
| `bridge/protocol.py` | Pinned offline schemas and byte framing |
| `bridge/client.py` | Session, capabilities, revision state and leases |
| `bridge/launch.py` | Token FD, supervised UI and local presentation channel |
| `qml/ShellState.qml` | Presentation store and 70 ms interpolation buffers |
| `qml/theme/Tokens.qml` | Colors, typefaces, spacing, motion and sound preference |
| `qml/components/Director*.qml` | One component for each Director view |
| `qml/components/MapView.qml` | Shared chart/minimap and marker interactions |
| `qml/components/Hud.qml` | HUD composition; objective, vehicle, notice and prompt presentation |
| `qml/components/Warp.qml` | Full-screen transition presentation, without input authority |
| `qml/components/Seal.qml`, `Constellation.qml`, `Reveal.qml` | Original graphics and reveal motion |
| `dev/` | Isolated compositor, SDK supervisor, scenarios and capture loop |

Alternative shells can reuse the protocol behavior without importing this
presentation. Change tokens or replace components rather than placing UI in
world packages. The development backdrop, projected marker samples, vehicle
readout and preview quest checklist are fixtures; they do not pretend to be
camera, vehicle or gameplay state from production core. Local manifest metadata
is a trusted launcher hint, not a filesystem discovery or polling mechanism.

M0 settings are session-local. Extension approval is deliberately absent: no
public approval RPC exists and no third-party executable extension is launched.
World art, physics, window pixels and compositor hooks stay outside this repository.

## Validation and license

See [VERIFICATION.md](VERIFICATION.md) for tested versions, screenshots, codec
checks and remaining limits. Schema provenance is pinned in `protocol/SOURCE.json`
and `protocol/MOCK-SOURCE.json`, with 0.2 provenance in `protocol/v0.2/SOURCE.json`;
vendored schema files retain their MIT license.

MIT; see [LICENSE](LICENSE). All shell iconography and procedural graphics are
original. The prototype was used for design lessons and visual ideas only.
