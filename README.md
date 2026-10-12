# Hyprune shell

> **Hyprune** is an explorable, world-driven desktop environment for Hyprland: your workspaces become places you can walk through, with live windows on the walls. This repository is the reference **shell**: the Quickshell HUD, Director, settings and overlays. Install Hyprune through the [hyprune](https://github.com/hyprune/hyprune) repository (starter kits, Nix, Arch); learn more at [hyprune.com](https://hyprune.com). Licence: MIT.

Quickshell HUD and Director for a world-driven desktop. Shell 0.2.0 supports exact
IPC 0.1–0.23 (one vendored pin per version under `protocol/`) and world formats up to 0.9. The shell launcher
defaults to the newest pin; `--protocol` or
`HYPRUNE_PROTOCOL` can explicitly select an older contract. The first real session runs against core through the
locked `../core/dev/hyprune-dev up|smoke|record` launcher. Core supplies the current
world metadata, safe SVG map, places, output descriptor, projected markers and
workspace locations. No launcher package paths are needed for that session.

Hold Tab in exploration to open the Director; core owns the configurable 1000 ms hold in M3B. The
bridge binds its direct Quickshell child, core verifies the actual Wayland HUD
credentials, and the Director maps only after exclusive overlay acceptance.
Escape closes it; F12 returns to the desktop. HUD/warp remain passive and only
on the world monitor. Map supports waypoint, travel and collision-checked
autodrive. Workspaces opens the mapped location using core's loading lifecycle.

Adventure is the default HUD concept; Settings → Appearance also offers
Instrument and Minimal. In IPC 0.15, tool 5 opens the window pocket. Tool hints
use core's Primary / Secondary / Alternate / Cycle labels and configured
bindings, switching to global gestures while Super is held. See
[the Placement HUD contract](docs/proposals/placement-hud.md).

IPC 0.21 (RFC-0012) adds a **Quests** tab directly after Map: quests grouped Active
(tracked first), Available, Completed and Failed or abandoned; details with per-objective
Track, Set waypoint, Show on map, Start focus session and Mark done; a personal quest form
(title, one step per line, an optional workspace, area or place, focus sessions per step)
that also edits. Keys: arrows, Enter, T track, Space mark done, F focus session, N new.
The HUD shows the tracked quest under the status, a focus timer chip (ring, mm:ss on core's
monotonic clock, phase, cycle dots, a quiet credit arc) and toasts (step done 3 s, quest
complete banner 5 s, focus phases 4 s; at most three, repeats merged, deferred to the break
in calm mode). Settings → Guidance edits markers, notifications and focus settings through
`guidance.get` / `guidance.set`. The bridge requests `quest.control` only at 0.21. The
Director hold ring waits 180 ms (`holdRingDelayMs`) so a TAB tap never flashes it.
`./dev/run quests` captures all of it from the mock with dev preview data.
Against a real 0.21 core, `dev/quests-core.py` runs inside core's nested harness (headless
hosts: `python3 $CORE/dev/nested/isolated.py dev/quests-core.py`, `HYPRUNE_CORE_DIR`
selects the core checkout) and reports each check; `dev/quests-demo.py OUT.mkv` records the
same features in Lumen Reach.

IPC 0.22 (RFC-0011 P1) adds an **Objects** tab directly after Quests with two views.
**Catalog** shows every catalog entry (`objects.catalog`, refreshed when the tab opens and
when `objects.catalogRevision` changes) as a card: thumbnail (or a cube), name, a World /
Library / Mine badge, size in metres, trait chips, triangles and GPU memory; filters by
source and category and a search over names and tags; entries that can't be placed are
dimmed with core's reason and invalid ones list their errors. **Add to pocket** (or Enter on
the focused card) calls `objects.pocket`; core selects tool 5 and a toast says so.
**Placed** lists this world's authored and user instances with their state (blocked ones
name the placement rule), their instance id and a lock badge; the configure panel shows the
instance id (`ID  u-3f9a1c`) and is built from sections in a fixed order (Transform, Lock,
Remove / Reset or Hide / Reset, and Data: for a machine, `Data source id: u-3f9a1c`, the
`com.hyprune.sources.<id>` source it reads by default, which a sources.json entry with that
id publishes; RFC-0013 draft), with "Show and reset authored objects" and "Remove my
objects" behind a second press, and user placement usage against core's limits. Keys: Up /
Down move, Enter adds or edits, / searches, V switches the view, L lock, H hide, R reset,
Delete remove. The tool 5 HUD lists pocketed objects (cube glyph, the selected one
highlighted) and shows a selected object item in the placement card; tool 4 shows the
gizmo space, pivot and snap. Object and library refusals become short toasts with core's
message and the placement rule. The bridge requests `objects.control` only at 0.22.
`./dev/run objects` captures all of it from the mock with dev preview data
(`HYPRUNE_DEV_PREVIEW=nested` captures on the nested window's output where the GPU can't
allocate headless buffers; stills go to `HYPRUNE_OBJECTS_SHOTS`, default under `/tmp`).

IPC 0.23 (RFC-0011 P2) adds characters. In **Objects → Catalog** a character entry shows
**Spawn**: the step that opens lists, under "Choose route", **Stand here** (a spot in front of
the player), this world's package and user routes from `paths.list` (each with its source;
routes core reports as not walkable, or already walked by 8 characters, are disabled with
core's first problem) and **Draw a new route**. Optional settings follow: speed (0.25–2),
start phase, direction, an accent colour and, for one of the player's own routes, its stops
(per point: seconds, a gesture or a seat id), saved with `paths.set`. Confirm sends
`npcs.spawn`, or `paths.draw {use: "route", spawn}` and closes the Director so the route is
drawn with tool 3; while `npcs.drawing` is set the HUD shows a hint and Objects shows a bar
with **Done** (`paths.finish`) and **Cancel** (`paths.remove` of the path being drawn).
**Objects → Characters** lists this world's characters (authored and the player's own) with
route or seat, activity and state; **Disable / Enable** (`npcs.disable`) works on both,
**Rebind route** (`npcs.bind`, or a freshly drawn route) and **Remove** (`npcs.remove`) on the
player's own; the motion setting (`graphics.set` `npc_motion`: auto, always, still, off) sits
on top with core's pause reason. Keys: V cycles the views; D disable, B rebind, Delete remove;
in the spawn step Up / Down choose, Enter confirms, Esc goes back. Characters no longer
appear in Placed.

On the HUD, the aimed character (`npcs.aimed`) shows a prompt under the reticle: "E  Talk"
(the prompt of its only interaction) or "E  Talk to <name>". A running interaction
(`npcs.interaction`) is presented by type: `say` as a compact caption (speaker, line n / m,
"E · next"); `choose` as a choice list that takes the keyboard (the bridge holds exclusive
input as for the capture note; Up / Down, Enter, 1–8 or a click call `interaction.choose`,
Esc ends it with `null`); `panel` opens the Director on that tab (`map`, `quests`,
`objects`, `characters`, `help`, … ; unknown ids only end the interaction); `waypoint` and
`guide` show a short toast. Character and route refusals and the `npc.*` / `path.*` notices
are toasts with core's words. `./dev/run npcs` captures all of it from the mock with dev
preview data (stills go to `HYPRUNE_NPCS_SHOTS`, default under `/tmp`).

The **Library** tab (RFC-0015 registry, phase 1) sits directly after Objects and works
through the `hyprune` CLI, not core IPC: the command is `$HYPRUNE_CLI` (a command line split
on spaces, for example `HYPRUNE_CLI="node /path/to/sdk/dist/src/cli.js"`), else `hyprune` on
`PATH`. It reads `hyprune source list --json`, `hyprune browse --json` (the cached indexes,
no network) and `hyprune content list --json` when the tab opens and after every job.
**Browse** shows each entry as a card: the verified cached thumbnail the CLI returns (never
a URL from an index) or a placeholder, name, creator, type, the source label as the CLI
words it (`Official`, `Community registry`, `Custom: <label>`), the declared licence with
its source-kind wording (reviewed by Hyprune; declared by the creator, not reviewed;
declared by the package, not checked), the download size and badges for installed, update
available and "needs a newer Hyprune"; filters by source and type and a search over names,
summaries and tags. **Install** and **Update** first run the command with `--plan --json`
and show the plan: name, id, tag and version, type, source label and URL, creator,
repository and commit, licence wording, download and installed size, the shortened sha256,
the libraries it pulls in and "Worlds and libraries contain no code. Installing doesn't run
anything." Confirming runs it again with `--yes --json`; a plan with a source change needs a
second, explicit confirmation before `--accept-source-change` is passed. The stages and
download progress follow the JSON lines; errors show the CLI's message and rule. A finished
library install refreshes the object catalog, and **Open in Objects** shows it there; a job
that finishes while the Director is closed shows a toast. **Installed** lists every install
with its current and previous tag, source (or `system`), pin and newer tag, with Update,
"Roll back to <tag>", Pin / Unpin and Remove (a second press); system-managed installs are
read only. **Sources** lists each source with its kind, location, entries, last refresh and
error, with Refresh, Disable / Enable and Remove (custom sources, a second press), and an
**Add source** form (an `https://` index or package URL, or `github:owner/repo[/name]`; a
label of up to 48 characters; the sha256 for a direct `.tar.zst` URL) with the notice
"Hyprune doesn't check custom sources. Packages from them are installed with the same safety
checks, but nobody has reviewed them." All index text is plain text and no link is opened.
Keys: V switches the view, / searches, Up / Down move, Enter installs or updates, U update
and P pin (Installed), R refresh (Sources); in the plan Enter confirms and Esc goes back.
`./dev/run library` captures all of it against `dev/fake-hyprune-cli.py` (stills go to
`HYPRUNE_LIBRARY_SHOTS`, default under `/tmp`).

IPC 0.19 adds Settings → Movement (field of view 30–120°, walk/run speed, view bob,
grab/mount/placement reach) and Settings → Reticle (style, colour, size, thickness,
gap, opacity, outline, dynamic, with a preview), backed by core's `player.get` /
`player.set`. The shell sends the reticle, valid and invalid colours from the HUD
theme with `overlay.style`, and dims the primary tool hint while the reticle is out
of range or invalid. `./dev/run player` captures both sections from the mock using
dev preview data.

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
python3 -m pip install --require-hashes -r requirements.txt   # exact, hash-pinned (dev/pin-requirements.py)
./dev/run
```

This launches the SDK's actual IPC 0.2 `MockDaemon` with
[dev/scenario.json](dev/scenario.json), plus this shell in a visible nested Wayland
window. `preview` is an alias. The SDK owns the 350 ms hold timer; a supervisor
trigger feeds its `hold` API and the shell receives `ui.opened`. Ctrl+C stops the
run. `HYPRUNE_SDK_DIR` selects another checkout (default: the sibling `../sdk`);
the tested pin and adapter hooks are recorded in `dev/SDK-SOURCE.json`. Capture
harnesses write screenshots under `$HYPRUNE_GALLERY_DIR` and finished videos under
`$HYPRUNE_VIDEO_DIR`. Set them in the environment or in an optional
`~/.config/hyprune/dev.env` (`$XDG_CONFIG_HOME` if set): one `KEY=VALUE` per line,
`#` comments, `~` expanded; the environment wins. Unset, the harness prints one
warning and writes to the ignored `dev/.run/gallery/` and `dev/.run/videos/`.
`dev/devenv.py` prints the effective values. Machine-specific values like these
never go into the repository.

```sh
./dev/run tour          # six views, then a native world load
./dev/run strict        # faithful SDK behavior; exclusive Director unsupported
./dev/run check         # IPC 0.2 + 1080p visual smoke check
./dev/run check-window  # visible 1280x720 composition check
./dev/run capture       # screenshots, 20–40 s video and recovery checks
./dev/run brand         # logo mark captures (Director, Settings About, Performance; Night/Paper; scales 1/2/1.25, 4K)
HYPRUNE_SKIP_RECORD=1 ./dev/run capture
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
```

Every nested lifetime is wrapped in `flock /tmp/worldshell-nested.lock`. The
harness reads the child compositor's startup environment, rejects the outer
signature/display, gives every `hyprctl` call an explicit child signature and
`qs ipc` its exact child PID. It never controls the host session. Interactive
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
| `qml/components/BrandMark.qml`, `brand/` | Hyprune mark in the theme colour; vendored masters and provenance in `brand/BRAND.md` |
| `Seal.qml`, `Constellation.qml`, `Reveal.qml` | Original graphics and reveal motion |
| `dev/` | Locked SDK/core harnesses, scenarios and review capture |

Alternative shells can reuse protocol behavior without importing this look.
Manifest hints are approved reads once, not filesystem discovery. M0 preferences
are session-local. No executable extension, world art/physics, compositor hook,
or invented approval API is shipped here.

See [VERIFICATION.md](VERIFICATION.md) for results and capture paths,
[NOTES-rfc-gaps.md](NOTES-rfc-gaps.md) for deferred contracts and core interop issues.
Schema provenance is in `protocol/SOURCE.json` and `protocol/v0.2/SOURCE.json`.
MIT; vendored schemas retain their license. All shell graphics are original.
The Hyprune logo is CC-BY-4.0 ("Hyprune logo by Hyprune contributors"); see `qml/components/brand/BRAND.md`.

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

Live follow-up: Workspaces includes native desktops and apps even without
configured world homes, via the amended IPC 0.6 inventory (up to 128 apps).
Director uses anchored page geometry after the Qt 6.11 StackLayout crash.
The launcher owns the authenticated bridge across QML restarts; same-UID owned
replacement children reconnect and bind their actual Wayland PID. No credentials
are exposed to QML. Back in world control gives a real cursor for native layers;
Back/Super+Tab returns. The full live cursor checklist remains in core/docs/M3B.md.
Invalid complete core frames are quarantined with redacted diagnostics and a
fresh snapshot. The updated core supervisor renews one-use credentials after
bridge disconnects; see [recovery and nested verification](docs/bridge-recovery.md).

World-anchored waypoint labels, the active route and E/F prompts are drawn by
core with the camera of the current frame. IPC 0.6 hides its projected HUD marker
repeater; older protocols retain it. Director, notices, compass and minimap stay
in the shell. Settings can enable optional area/place labels. The shell sends a
lease-scoped `overlay.style` update (colours, font family and optional PNG icon
atlas) when the lease or theme changes; core validates and applies it outside the
render pass. Without an atlas, core uses its bundled vector waypoint/prompt icons.
In world mode U captures a JSON/PNG pair; interactive, focus and menu use Super+U,
which leaves U and Y available for ordinary typing. F3 toggles diagnostics in
those modes; world also accepts Y.

The responsive layout, curved HUD, IPC 0.7 graphics controls and automated
resolution/scale evidence are documented in [POLISH.md](POLISH.md).
