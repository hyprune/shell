# HUD concepts and package styles

Hold TAB for the Director. **Settings → Appearance → HUD concept** selects
Vanguard, Instrument or Minimal. **5** cycles them in world mode on IPC 0.9+;
Input bindings exposes `hud.cycle`. Changes show a centre banner and save
immediately. Application and Director text input retain ordinary key 5.

Vanguard has large accent tiles and a spacious subtype plane; Instrument adds
coordinates, denser geometry and cyan accents; Minimal reduces radar, tiles and
secondary text. Shared components show actual core tools/subtypes, circular local
radar, transparent compass rails, zone titles and the core-timed TAB ring.
The projective matrix brings inner edges forward on a convex surface, with the
outer left/right/top edges receding; flattening output depth avoids
Qt's 2D clip volume. The upper-right small-text cluster uses 35% of the selected
curvature and a texture at twice its physical output size (including output and
HUD scales) before projection. Its padded texture preserves the shadow; the
radar caption stays upright. Default HUD text has solid curve-rasterized glyphs
and a 50% dark shadow, with 1.5 logical pixels of blur and a 0.5-pixel downward
offset (about 2–3 physical pixels of blur at 4K). Label textures are supersampled
before perspective; only the shadow is blurred. Small text uses semibold weight.
The radar caption and upper-right status labels also have tightly fitted black
scrims (72% opacity, feathered edges). Core has no regional background-luminance
telemetry, so these use the fixed fallback rather than screen capture in normal
operation. Glyph fill and the dark-world shadow remain unchanged. Real padding
around the status cluster keeps the feather inside its supersampled texture
without stretching the text.
World styles can explicitly request `stroke.style: "outline"` to retain native
outlines; omitted styles and `shadow` use the soft shadow. HUD input regions
remain empty. Menus and
core world markers stay flat.

Appearance includes curvature On/Off and strength (default 80%), resource bar,
and **Use world HUD styles**. GPU/CPU show measured render time against target
frame budget, not system utilisation. Missing RAM telemetry explicitly falls
back to GPU. Tool capacity shows path points or locked windows; other tools show
unavailable. Preferences: `$XDG_CONFIG_HOME/hyprune/shell.json` (normally
`~/.config/hyprune/shell.json`). Test runs use private files.

**Performance** is a dedicated Director tab. Auto shows its resolved quality;
overrides display Custom. Renderer policy/power, dynamic scale bounds and nullable
GPU costs use exact IPC 0.10. Older 0.7–0.9 cores retain original controls with
explicit unavailable states. Shared timings are never presented as isolated or
additive effect measurements. Selecting a preset clears effect overrides;
independent frame/scale/renderer choices stay explicit. Core owns handover/policy. Native FPS and the admitted offload FPS ceiling are labelled separately.

World style format: [world-hud-style.md](proposals/world-hud-style.md).
Only launcher-authorised `--world-package /package/world.json` paths currently
supply skins; authenticated package discovery is requested from core. No executable
style code or layout changes. Fonts and sanitised icons use a private immutable
cache. Invalid theme, world exit and opt-out restore concept defaults; invalid
optional assets fall back by role. Original sample: `dev/styles/signal-amber`.

## Automated validation

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -q
./dev/run hud-check
HYPRUNE_NESTED_PROTOCOL=0.13 flock /tmp/worldshell-nested.lock python3 dev/hud-concepts.py
```

The harness verifies its own child compositor/headless output and owns teardown;
never target the owner session or stop the gallery autocommitter.
`HYPRUNE_HUD_QUICK=1` limits captures and skips video. Full run covers four Lumen
Reach homes, three concepts, 1080p/1440p/4K at scales 1 and 2. It checks real key 5,
wheel subtypes, hold animation/cancel, persistence, graphics dropdowns against
core state, and package styles/opt-out/world exit. Output: gallery
`screenshots/hud-concepts/`, `videos/hud-concepts.mp4` and a string-only sidecar.
Video encodes in `/tmp`, then moves into the gallery when complete.

`HYPRUNE_HUD_REVIEW=1` captures the upper-cluster/Performance follow-up without
recording another video: three concepts in Sun Court and Rime Vault, all six
resolution/scale combinations, plus flat/curved and USB-C policy comparisons.
Original filenames are preserved and new captures have a `-v2` suffix. Shared
world shading appears once above the effects; only independent measurements
appear beside individual controls. Power policy is a human-readable sentence.

`HYPRUNE_HUD_CONVEX=1` captures the direction/calibration follow-up as `-v3`:
all concepts in bright/dark homes at all six resolution/scale combinations,
plus flat/default/maximum comparisons. It leaves older captures intact.
`HYPRUNE_HUD_TEXT=1` captures the same bright/dark matrix as `-v4`, with
flat/default comparisons and an explicit world-outline/opt-out pair.

`HYPRUNE_HUD_CONTRAST=1` adds the `-v5` bright-background regression matrix.
It captures all concepts in Sun Court and Rime Vault, plus white-background
stress cases at each resolution/scale. Run under the same flock:

```sh
HYPRUNE_HUD_CONTRAST=1 flock /tmp/worldshell-nested.lock python3 dev/hud-concepts.py
python3 dev/hud-contrast-sheet.py
```

The development-only `preview.contrastProbe` endpoint can hide the text while
keeping its scrim, or render white glyph masks over black. It has no effect in
normal operation and does not capture the screen itself. Numerical evidence
uses the three static Vanguard labels to avoid changing frame-stat strings.
Text/background/mask crops are retained in gallery `contrast-v5/`, and
`contrast-v5-measurements.json` records bounding boxes and unrounded results.

Two gates must pass at 4.5:1: nominal foreground versus the brightest captured
background beneath glyph ink, and the minimum actual rendered glyph-core
contrast against the text-free background. Glyph cores have ≥80% coverage in
the mask; partially covered antialiasing edges are excluded explicitly. The
calculation uses linearised sRGB luminance and `(Llight+.05)/(Ldark+.05)`, following
[W3C contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
World frames are sequential captures; the static pure-white stress case supplies
a conservative background bound without scene-motion differences. This is
capture evidence for these default labels, not a general accessibility claim
for arbitrary fonts, world styles or the entire HUD.

The v5 crop sheets retain v4 beside v5 and add measured contrast in a third
column; scale 2 has a separate sheet. The private reference is not needed or
copied for this regression check.

## Convex calibration

The supplied private reference, widescreen reference captures
([source](https://example.invalid/reference)), and the HUD designer's gameplay
captures ([source](https://elsamadisy.com/game_ux.html)) were reviewed before
tuning. Native-pixel endpoints on four lower-left box borders give
apparent slopes of approximately 2.4°, 2.9°, 3.2° and 3.0° upward toward centre.
The upper-left objective rule slopes about 2.4° down toward centre; the supplied
upper-right notice rule slopes about 2.8° in the opposite horizontal direction.
These are screen angles, not recoverable physical camera/yaw angles. Manual
endpoints have approximately ±2 px uncertainty (±3 px on blurred captures).
Edge-height ratios are approximately 1.00–1.05, with greater relative uncertainty.

At 80% strength, the 590×203 tool deck has 3.24°/2.37° rising top/bottom borders
and a 1.049 inner/outer edge-height ratio. Opposite sides mirror exactly; the
upper edge of top clusters recedes. Yaw and pitch reach 16° at maximum strength,
with an inward tangent tilt of 3.5° and camera distance `max(500, width*5)`.
The rotation order avoids a yaw/pitch cross term reversing the border slope.
The existing slider value and saved preferences remain valid; its geometry is
recalibrated. Upper-right supersampling/reduced curvature and the upright radar
caption remain in effect. Tests assert visible corner geometry and angle bands.

Downloaded images, pixel endpoints, source metadata and reference crop sheets
are private gallery files under `reference/hud-curve-v3/`, locally excluded from
Git before download. No reference artwork is included in the shell or docs.

Development-only `preview cycleHud` uses the same persistence/banner path.
`concept`, `resource`, `curvature`, `worldStyles` support capture automation;
always target the verified nested Quickshell PID. Mutations require explicit
`HYPRUNE_DEV_AUTOMATION=1` or a development fixture.


## Results

58 shell tests, 92 schema tests, SDK mock skin/font/icon smoke and the docs build
passed. The full core 0.10 run produced 72 HUD matrix captures plus menus, styles,
flat/curved and event comparisons; its 52.9-second video uses real core key 5.
A dedicated watchdog-bounded menu test switched Intel → NVIDIA → Intel and
verified Auto's USB-C policy rejection. Legacy IPC 0.8 hold/graphics/workspace
regression also passed. See `evidence/hud-concepts.json` for measured values.
Only dynamic package discovery and RAM/system CPU telemetry remain core requests;
the sample skin works through an authorised package path.

Gallery review follow-up: 61 shell tests and the SDK mock check passed. The
locked core 0.10 run produced 51 `-v2` captures: all concepts in Sun Court and
Rime Vault at 1080p/1440p/4K, scales 1/2, Performance top/bottom at each size,
flat/curved comparison and the USB-C Auto policy. Every capture passed the
layout audit and the shell log contained no QML errors. See gallery
`screenshots/hud-concepts/review-v2-verification.json` for the core snapshot.

Convex follow-up: 61 shell tests (including projected-corner direction, mirrored
sides, monotonic strength, measured default angle bands and identity when off),
the SDK mock and locked core 0.10 capture run passed. All 45 `-v3` captures passed
layout audits without QML errors: 36 concept/home/resolution/scale shots and nine
flat/default/maximum comparisons. Evidence: gallery
`screenshots/hud-concepts/convex-v3-verification.json`. Private comparison sheet:
`reference/hud-curve-v3/flat-curved-reference-v3.png`; endpoints and uncertainty:
`reference/hud-curve-v3/measurements.json`; download attribution: `sources.json`
in the same private directory.

Text follow-up: 61 shell tests, the SDK mock, and the locked core 0.10 run passed.
All 44 `-v4` captures passed layout audits with no QML errors, including the
explicit world-outline and opt-out pair. The gallery includes 24 separate status
and radar-caption crops and `screenshots/hud-concepts/hud-status-crops-v4.png`
(v3/v4 comparisons in both homes at three resolutions). The private reference
sheet is updated at `reference/hud-curve-v3/flat-curved-reference-v4.png` and
remains excluded from Git.


Bright-background follow-up: 65 shell tests, the SDK mock, and the locked core
0.10 run passed. All 50 `-v5` captures passed layout audits with no QML errors.
All 54 static-label measurements passed both 4.5:1 gates. Minimum rendered
core-pixel contrast: **6.62:1 Sun Court**, **6.28:1 Rime Vault**, **5.93:1 pure
white**; minimum nominal contrast over pure white was **8.22:1**. Default solid
fill, soft shadows and explicit world outlines are retained. The gallery has
24 standalone status/caption crops and two v4/v5 sheets with contrast columns:
`screenshots/hud-concepts/hud-status-crops-v5.png` and
`hud-status-crops-s2-v5.png`. [Recorded results](evidence/hud-contrast-v5.json).


## Cursor and climbing (IPC 0.12)

This follow-up introduced exact **0.12**; explicit older selections remain
supported. Canonical 0.11/0.12 schemas are pinned separately with their hashes;
climbing comes from 0.11, and cursor mode from 0.12. Recording/replay contracts
are validated without adding automatic recording or replay actions.

Back / Super+Tab switches to the real cursor. A passive **CURSOR · Back /
Super+Tab to return** chip replaces the bottom action hints on the same curved
plane. Vanguard uses its accent stripe, Instrument a technical border/mono font,
and Minimal a smaller stripe and restrained scrim. TAB/use/focus/scope and
subtype-action hints disappear; the status label says **NATIVE POINTER**.

While climbing, a small original ladder indicator and core's `movement.prompt`
replace the tool cluster's secondary stats. Empty prompts fall back to
**W/S climb · Space let go**. The text wraps/elides safely. Cursor mode wins over
climbing, including stale activity snapshots; releasing the climb removes the
prompt. Core continues to own all keys, cursor routing and climbing behavior.

```sh
HYPRUNE_HUD_INTERACTION=1 flock /tmp/worldshell-nested.lock python3 dev/hud-concepts.py
```

The check exercises both actual toggle gestures, all three climbing mechanics,
all concepts, 1080p/1440p/4K scale 1 and compact 1080p scale 2. It asserts actual
visible QML items, exact core prompt text, no truncation, native cursor visibility,
frozen movement, return and Space-detach behavior. Screenshots are in gallery
`screenshots/hud-concepts/{climb,cursor}-*-ipc012.png`.

Integration note: core `0a4c6d1` still sets `PROTOCOL = '0.10'` in
`dev/live/live.py`. That explicit launcher argument must move to 0.12 for the
new HUD states in the owner's next live launch. Shell does not override an
explicit negotiation or edit the core-owned launcher. Nested verification
launches 0.12 explicitly; no live-session commands were used.

Core follow-up found in the screenshots: its centre **Move into ladder to climb**
hint is still drawn during cursor mode. The prompt generation in
`core/src/platform/hyprland/Plugin.cpp` (around line 3337 at `0a4c6d1`) checks
walking/noclip/typing but does not exclude suspended free-cursor mode. Core must
suppress its own interaction prompts there. Shell cannot hide a prompt baked
into the world frame; its own climb/tool/footer prompts are verified hidden.
See `cursor-vanguard-1080p-s1-ipc012.png` for direct evidence.

Validation: **67 shell tests**, the SDK 0.2 mock compatibility check, and **12
real-core 0.12 concept/resolution cases** passed. The locked run captured 25
screenshots with no QML/schema/layout errors. [Recorded results and core
follow-ups](evidence/hud-interaction-012.json).


## Ink, visibility and authored cameras (IPC 0.13)

The launcher defaults to exact **0.13**. Performance → **Ink & visibility** adds
Preset/Off/On ink permission, an independent GPU cost covering geometry
normals/depth plus edge ink, authored-visibility culling and submitted/culled/total
batch counts. Worlds without an authored outline stay unoutlined when On is
selected. Older protocols show an unavailable message and never receive either
new graphics patch key; selecting a preset clears the outline override only on
0.13.

Width (1–4 logical pixels) and `#RRGGBB` colour edit the loaded world's existing
ink profile through `atmosphere.get/set`; the bridge merges only those fields
into a fresh profile. They apply live **until world reload**. Reset colour restores
the colour first loaded in this shell session. No style is invented for worlds
without one. Core 0.13 has **one fixed native geometry-edge quality**, so the
quality row is disabled and says so; a genuine quality selector still needs a
core contract. There are no persisted graphics width/colour override fields in
0.13, and the UI does not promise persistence for these atmosphere edits.

World packages 0.3, 0.4 and 0.5 now validate through a separate canonical world
registry, including 0.5 ink and visibility metadata. Frozen IPC common-schema
pins are unchanged. The exact 0.13 IPC pin is also unchanged: its top-level
`oneOf` has overlapping generic/photo/release revision-response branches, so the
shell uses their union at the envelope. Each response is still validated against
its originating method. The schema repository should correct this overlap.

The shell never requests `camera.author`, `camera.photo` or `camera.release`.
On 0.13 it polls the read-only `camera.get` at 4 Hz while active. HUD content stays
hidden until the first lens sample and during `held:true`; the transparent
Wayland HUD window remains mapped to preserve verified shell association and
its lease. Release, author disconnect or a world change restores the normal HUD
after a fresh lens sample. Director controls remain independent. Capture tools
should wait for this poll (up to 250 ms plus response/render latency) before
capturing a held camera. The dev `preview.status` reports `hudVisible` and camera
state for deterministic waits.

```sh
HYPRUNE_HUD_AUTHORING=1 flock /tmp/worldshell-nested.lock python3 dev/hud-concepts.py
```

This uses core's authoring grant for the **test client only**, launches the real
shell with normal grants, loads the 0.5 visibility laboratory, and exercises
actual keyboard controls for ink, width, colour/reset and culling. It captures
Performance at 1080p/1440p/4K and compact 1080p scale 2, then holds a 90° rolled,
15° FOV, shifted-lens camera. HUD hiding, fixed pose, same-lease restoration on
release and author disconnect are asserted. Evidence:
`docs/evidence/hud-authoring-013.json`; gallery `performance-ink-*-ipc013.png`,
`photo-held-ipc013.png` and `photo-released-ipc013.png`.

Validation against core `2494c13`: **74 unit tests**, the SDK mock HUD check,
and locked real-core **0.12 and 0.13** acceptance runs passed. The older-core run
selects a preset through the actual menu and verifies no 0.13-only keys are sent:

```sh
HYPRUNE_HUD_GRAPHICS_COMPAT=1 HYPRUNE_FOLLOWUP_PROTOCOL=0.12 flock /tmp/worldshell-nested.lock python3 dev/hud-concepts.py
```

Integration note: that core revision's `dev/live/live.py` still explicitly picks
**0.12**. Its launcher must select 0.13 to expose these additions in the owner's
session; the shell respects an explicit older version. No live-session commands
were run for this work.
