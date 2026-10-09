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
- **100 unit tests pass**, including repeated invalid snapshots, malformed JSON,
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

## In progress / limits

- A stronger regression requiring two explicitly unzoned mount instances is
  unfinished. First, recall produced no instances; then tool-5 clicks timed out
  waiting for two unzoned instances. Neither attempt proved the specific mount
  projection end to end. The failed fixture additions were removed from the
  checkpoint harness; do not call this strengthened check passed.
- The final schema pin has unit coverage but still needs the real nested rerun
  with a deterministic unzoned-window fixture. Core's agent is also implementing
  this replay; read `../core/docs/CHANGES-FOR-SDK-AND-SHELL.md` before duplicating it.
- The **1080p @ 2× Placement panel is too large**. This is an open visual issue,
  not fixed in this checkpoint.

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
6. Separately fix Placement sizing at 1920×1080, output scale 2 (960×540 logical).
   Inspect the tile, window-info card, hints and count badge together; constrain
   cluster dimensions to available logical viewport, elide long titles/classes,
   and retain readable configured hints. Capture all three concepts at scales
   1/2 and 1080p/1440p/4K in nested; keep this separate from recovery changes.

## Safety / open coordination

- Nested only under `/tmp/worldshell-nested.lock`. Never run launcher or qs
  against the owner's actual compositor. No live restart or deployment occurred.
- Do not signal the gallery autocommit process. No private art or identifiers were
  added to shell; the recovery evidence contains redacted shapes only.
- Core owns its source and shared IPC handoff document. Renewal and empty-area
  projection fixes are core dependencies; confirm its final commit with the lead.
- No recovery test process remains running. Nothing was pushed. Commit trailers:
  `Co-Authored-By: Krombopulos Michael <Krombopulos.Michael@mail99.me>`.
