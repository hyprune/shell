# First-session integration update

IPC 0.3 closes verified shell-child association/exclusive input, selected-output
delivery, package Map delivery and core marker projection, plus trusted
workspace-location mapping/activation. The real nested smoke verifies the shell
against core, including live station app typing and workspace warps. See
core/docs/FIRST-SESSION.md in the sibling repository and RFC-0003/0004/0008's
first-session amendments. Production renewal, persistent user bindings, arbitrary
transformed outputs and the remaining extension hosts are still follow-up work.
The notes below preserve the earlier review; their real-session blockers are
superseded by that explicitly negotiated 0.3 contract.

# Shell M0: RFC gaps and disposition

Read RFC-0001/0003/0004/0005/0006/0008 and the local IPC/world schemas. M0 began
against schema `96dad32178b14d0c50f64413430d054133d40425` (IPC/world 0.1), with
SDK preview `3ab86cb`. The M1 IPC 0.2 amendment landed during development and then
added stable warp IDs, world loading and output identity to transition samples.
The tested amended schema is `c07a923f1f44f48c00daad1662fb19b05047b735`;
docs origin/main is `114387dbd13a1a779ffda9e81293814adc94fc85`. The core M1
integration notes were read. Vendored digests are in `protocol/v0.2/SOURCE.json`.
These notes describe the verified 0.2 delivery; concurrent 0.3 integration work
happened separately and has not been assessed here.

These notes distinguish the initial omissions from the current amendment. The
shell does not widen a negotiated schema or patch upstream repositories.

## Director and input authority

IPC 0.1 has no core-owned panel-open event. The SDK mock uses `ui.open` as a method
and `ui.opened` as an event; the original M0 brief's `ui.open` event name was
ambiguous. M1 resolves this with canonical `ui.opened` / `ui.closed`, lease/output,
session and revision, core-owned 350 ms Tab hold, and the panel name `overview`.
Release leaves it open; Esc closes. The shell accepts `overview` or `director`,
checks ownership, then requests `shell.overlay` exclusivity before mapping.
Dismissal uses native `ui.close`; 0.1 falls back to `shell.overlay(false)`.

**Still blocked in real core:** M1 explicitly rejects `exclusiveInput:true` until
a trusted launcher verifies the shell's Wayland-client association. The bridge
and UI are separate processes; a connection token alone does not prove that
association. Interactive preview uses an explicit development association emulator around the
SDK mock; the faithful SDK also rejects exclusive input. The emulator checks the
authenticated shell, connection-owned lease and supervised Quickshell child.
No local production hold timer or binding is implemented. Core's emergency escape
must work independently of the shell, including while warp is passive.

Needed: a ratified bridge/Wayland-child association mechanism and real seat-routing
integration tests. Opening must not silently grant input before core accepts it.

## World monitor identity

M1 clarifies that `runtime.outputs` contains the selected world monitor, retained
while inactive. IDs remain opaque; there is no association to a Wayland name,
geometry, scale or transform. Comparing these IDs to `QScreen` is not reliable.

M0 requires a trusted `--output opaque-id=Wayland-name` mapping, intersects it with
runtime outputs and actual UI screens, and claims one matching output only. Loss
or unplug unmaps the UI. The nested harness includes a second output.

Needed: versioned output descriptors and a stable mapping lifetime across
reconnect/hotplug, plus explicit lock presentation policy.

## Camera projection and presentation samples

The 0.2 camera methods describe placement; they do not provide the renderer's
projection matrix, viewport, occlusion or first/third-person camera relationship.
RFC-0008 explicitly defers projected markers. Movement state is not a license to
guess those properties. Ordinary pose samples still lack monotonic timestamps.

M0 interpolates heading/player position with a bounded 70 ms arrival-time buffer.
Projected samples are supplied only by an explicit dev camera fixture, buffered
separately and removed when its world is no longer current. Reduced motion
bypasses interpolation. Vehicle readouts are explicit presentation fixtures. The objective checklist is
shell-owned onboarding guidance, not claimed world quest state.

Needed: per-output projection or normalized projected-marker samples, monotonic
time, coordinate/clip conventions, camera generation and visibility/occlusion,
with bounded marker data and stale/disconnect behavior.

## Maps, world catalogs and spatial metadata

World 0.1 and 0.2 provide spawns, zones and anchors, but no map/SVG field. IPC world
state has only ID/spawn ID and no installed catalog, package digest or approved
asset retrieval. M1 moves zones/waypoint into revisioned `location`; this fixes the
mock's unversioned `world.metadata` channel, not map delivery.

M0 accepts explicitly approved manifest paths from its launcher and reads them
once. It uses spawn coordinates for a labeled **local schematic**, not a blueprint
of actual geometry. Zone banners use authoritative pose and supplied zone bounds.
No arbitrary package traversal or remote image loading occurs.

Needed: bounded versioned world/catalog retrieval, immutable digest and map asset
reference, world-to-map bounds/transform and validated resource delivery. Define
permitted SVG features; forbid scripts and remote resources.

## Waypoints, travel and workspace locations

IPC 0.1 lacks waypoint/travel/workspace activation. M1 resolves point/zone waypoint,
route and timed travel (`travel.start`, `travel.cancel`); targets are positions or
zone IDs. Native Map double click uses `travel.start`, with zero duration for
reduced motion. The SDK preview uses these same native 0.2 methods and Target shapes. Strict 0.1
keeps unsupported controls unavailable.

**Still absent:** workspace enumeration/activation and workspace-to-location
mapping. A `kind: workspace` surface is a future adapter, and `surface.focus` can
be refused. World loading is not equivalent to point travel.

The dev warp scenario explicitly maps mock workspace IDs to worlds; this is not
inferred production behavior. Needed: `workspace.activate` plus a bounded catalog
and validated location mapping, with core-owned routing and failure semantics.

## Warp and loading lifecycle

The initial 0.1 contract could not expose loading, progress or readiness. The
new 0.2 amendment now provides the required baseline:

```json
{
  "method": "location.transition",
  "params": {
    "sessionId": "session",
    "revision": 123,
    "id": "stable-operation-id",
    "outputId": "opaque-world-output",
    "monotonicMs": 456789,
    "phase": "loading",
    "progress": null,
    "to": {"worldId": "com.hyprune.garden", "spawnId": "arrival"}
  }
}
```

`phase` is loading/departing/travelling/arrived/failed/cancelled; `progress` is null
for indeterminate loading or 0..1. `to` is a world destination or point/zone target.
The matching revisioned `location.transition` state persists terminal results.
Core flushes loading events while world activation is pending; lock/Esc/F12 have
priority. Activation/arrival is atomic; failure retains the old world.

M0 verifies event session identity and keeps the revisioned state baseline intact.
Validated loading hints can present before a coalesced state delta arrives,
including while a world-load RPC is pending. Revision gaps clear hints until resync. It filters by leased
output, resumes mid-jump snapshots, does not replay terminal reconnect state, and
waits for the destination world/committed revision before arrival. No UI timer
invented progress is used. Reduced motion is a static destination card; optional
sound is off by default. The warp has no pointer region or keyboard focus.

The SDK checkout now implements real 0.2 (`86c04ab`). The recorded demo uses its
actual MockDaemon and native world-load delay, stable IDs and loading events.
There are no mock-only wire additions or notice-carried transitions. Two explicit
test adapters remain: verified-child association emulation and mock workspace
focus mapped to native `world.load`. They use pinned SDK private `execute` / `lease`
hooks and may need adjustment after SDK changes; provenance is in
`dev/SDK-SOURCE.json`. `./dev/run strict` disables them. SDK files are unchanged.

`./dev/run core-check` also exercises the actual plugin and `hypruned`: native
travel/warp/arrival, pending loading, Tab hold timing, exclusive refusal and F12
while warping pass. This does not prove exclusive seat routing, which remains
unsupported. Sound/preferences ownership and authoritative destination labels/art
still need a contract; current labels come from trusted manifests/location state.

## Coordinate semantics

Core M1 uses manifest spawn positions as capsule feet and Target/camera positions
as eyes. Its spawn activation adds 1.7 m (`Plugin.cpp`); the shell uses that offset
for manifest-derived waypoint/travel targets. RFC/schema do not explicitly expose
this conversion. Needed: a resolved spawn Target or agreed coordinate semantics
and player dimensions, avoiding a shell-maintained physical constant.

## Core startup interoperability found by the native check

At tested core `4d53c2d`, socket bind under `umask(0077)` creates mode 0700, while
RFC-0003 requires 0600. The production bridge correctly refuses it. The isolated
core harness verifies the owned nested socket and changes only that test socket
to 0600. Core should create/chmod it to the specified mode itself.

The public socket also appears before the plugin's full method advertisement.
An early hello can consume a one-use token with an incomplete method profile.
The test harness waits 300 ms before authenticating. Needed: publish the socket
only when the interactive method profile is ready, or an explicit readiness and
re-authentication contract. Production continues honoring the returned profile.

## Trusted startup, tokens and reconnect

M1 documents `HYPRUNE_SOCKET`, `HYPRUNE_PROTOCOL`, `HYPRUNE_CLIENT_ID`, and a one-use
`HYPRUNE_TOKEN_FD` containing 64 lowercase hex bytes plus newline. Fresh tokens
are required on reconnect. Core's private launch grant pipe is separate.

M0 retains the token FD in the bridge, never QML/argv/logs/files. The private UI
channel is an owned 0600 socket in a 0700 runtime directory, checks SO_PEERCRED,
and permits one UI connection. Same-UID unsandboxed code is trusted, per RFC.
The bridge identifies as `com.hyprune.shell`; grant injection must authorize that
ID. Socket/protocol environment names are supported. The development supervisor
renews tokens over a private duplex FD (`renew\n` -> fresh token line), while the
SDK CLI's one-shot FD supports initial authentication only.

Still needed: production supervisor renewal and explicit bridge/Wayland-child
association. Local IPC permissions are not a sandbox boundary. Reconnect obtains
fresh authority and a new snapshot; mutations are never replayed.

## Other shell contract gaps

Persistent prompt bindings, notice actions, movement-mode discovery, settings
persistence and extension approval data are not specified. M0 uses session-local
theme/motion preferences and advertised method availability; it does not launch
executable extensions or invent an approval RPC. Labels are plain text.

The mock checks client state/lease behavior, not compositor input arbitration.
Real-core emergency escape is tested. Before claiming full RFC-0008 conformance,
test real lock handling, exclusive seat routing, multi-monitor hotplug and failure
recovery with the trusted UI association in place. See [VERIFICATION.md](VERIFICATION.md) for tested limits.
