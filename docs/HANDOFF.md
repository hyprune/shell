# Shell handoff — 2026-10-09

## Done

- Recovery fix committed as `72a75a9` (not pushed). Complete invalid JSON/schema
  frames are quarantined, with bounded redacted method/path/rule/excerpt logs.
  The bridge requests a fresh snapshot and retries bad snapshots with backoff,
  keeping the established connection alive. Unknown framing boundaries reconnect.
- Supervisor renewal uses the existing inherited duplex token FD and `renew\n`
  contract, with a ten-second reply timeout. Core implemented the corresponding
  PID/UID-checked broker and persistent supervisor. Fresh tokens remain one-use;
  no token reaches QML, argv or files. Existing one-shot supervisors need a new
  launch to gain renewal; the owner's live session was deliberately untouched.
- Root cause: read-only post-warp capture states contained empty `areaId` on
  mount instances 0 and 1. HUD styles/visibility were not the rejected fields.
  The original log cannot identify the exact notification envelope retroactively.
- Canonical IPC 0.15 correction `d44126a0862367c4be2d4227fd9bd2068b0efb8e`
  is vendored with its hash: areaId is optional for unzoned instances, nonempty
  when supplied. Older shell protocol pins remain unchanged. Core removes
  unzoned mount metadata for older negotiated protocols.
- **100 unit tests pass** (rechecked after the Placement sizing fix), including repeated invalid snapshots, malformed JSON,
  redaction, burst throttling, and optional/nonempty areaId validation.
- **Real-core nested recovery run passed under the flock**: Lumen → local styled
  format-0.5 world with visibility regions; injected invalid delta recovered by
  snapshot on the same session; two forced socket disconnects reauthenticated and
  restored the HUD lease. No FD-exhaustion loop or QML errors. This run preceded
  the final schema repin. Redacted evidence: `docs/evidence/bridge-recovery.json`.
- `dev/recovery-core.py` and `dev/recovery-launch.py` retain that passing scenario.
  Fault injection exists only in the test launcher, preserving the real bridge
  PID and inherited credential FD. The harness always verifies nested identity.
- Earlier Adventure/Placement/generic gesture work is already committed through
  `ba67da2`; no additional HUD changes were made during this recovery task.

- **Placement sizing (step 6) fixed** in `2eeb691` (captures harness `15154ad`).
  Logical viewports under 800 px high (1080p @ 2×, 1440p @ 2×) use a dense
  tool-5 deck: 56 px tile, 3-row window card (title, class + client size on one
  row, both elided), hints on one row only when binding and label fit whole,
  otherwise stacked so chords never split. 960×540: deck 528×211 → 422×150
  (55%×39% → 44%×28%; six-action gesture overlay 52% → 39% high). 1080-logical
  and larger layouts are geometrically unchanged. Verified in nested via
  `dev/run placement-sizes` (SDK mock; 1080p/1440p/4K × scales 1/2 × three
  concepts; no layout-audit failures, no QML warnings). Before/after sheet:
  gallery `screenshots/placement-sizing-before-after-2026-10-09.png`.
  Not yet re-shot through real core (`HYPRUNE_HUD_PLACEMENT` in hud-concepts.py).

## In progress / limits

- Strengthened recovery regression **passed** (core agent, 2026-10-09) with the
  final schema pin: `dev/recovery-core.py` defaults to the generic visibility
  fixture, mounts real clients by tool-5 placement on the unbound world workspace,
  and asserts nonempty unzoned instances (areaId omitted) after each warp, after
  invalid-frame recovery and after both forced disconnects; only the injected
  frame is invalid and no reconnect occurs through the warps. Earlier attempts
  produced no instances because recall and free spawn poses do not survive a
  world load for unbound clients; only saved free-space placements do.
- Placement sizing at 1080p @ 2× is **fixed** (see Done → Placement sizing).

## Exact next steps

1. Read core's latest handoff and check its committed launcher/projection fixes
   and refreshed `build/live`. Do not edit core code or push any repository.
2. Run `python3 -m unittest discover -s tests -q` in shell.
3. Select a local format-0.5 package with HUD style and visibility regions via
   `HYPRUNE_RECOVERY_WORLD`; run:
   `flock /tmp/worldshell-nested.lock python3 dev/recovery-core.py`.
   The original private source package changed and failed core's UV validation;
   the previous passing run used the installed snapshot identified by read-only
   `~/.local/state/hyprune/live/state.json`. Never publish its path, name or assets.
4. Coordinate with core's deterministic warp replay to create genuinely unzoned
   placed windows. Assert nonempty mount instances, omitted areaId, valid 0.15
   state/delta, and no reconnect through the warp. Inspect actual queue/tool/mount
   counters if the fixture does not place windows; do not merely extend timeouts.
   Then repeat invalid-frame injection and both forced disconnects after the pin.
5. Update redacted evidence and validation notes with the final run. Local-only
   troubleshooting logs are `/tmp/hyprune-recovery-test.log` (latest failed
   strengthened attempt), `/tmp/hyprune-recovery-shell.log`, and
   `/tmp/hyprune-recovery-unit.log` (100 tests passed). They may contain private
   runtime details; do not copy them wholesale into a repo or gallery.
6. ~~Placement sizing at 1080p @ 2×~~ done (`2eeb691`). Optional follow-up: rerun
   the real-core placement acceptance (`HYPRUNE_HUD_PLACEMENT=1 flock
   /tmp/worldshell-nested.lock python3 dev/hud-concepts.py`) to refresh the
   gallery's `*-pocket-*-s2-ipc015.png` shots with the dense deck.

## Safety / open coordination

- Nested only under `/tmp/worldshell-nested.lock`. Never run launcher or qs
  against the owner's actual compositor. No live restart or deployment occurred.
- Do not signal the gallery autocommit process. No private art or identifiers were
  added to shell; the recovery evidence contains redacted shapes only.
- Core owns its source and shared IPC handoff document. Renewal and empty-area
  projection fixes are core dependencies; confirm its final commit with the lead.
- No recovery test process remains running. Nothing was pushed. Commit trailers:
  `Co-Authored-By: Krombopulos Michael <Krombopulos.Michael@mail99.me>`.
