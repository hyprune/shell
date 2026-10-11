# Warp validation and bridge recovery

The live captures immediately after the world switch contained empty strings at
`/mounts/instances/0/areaId` and `/mounts/instances/1/areaId`. Both violate the
nonempty slug contract. HUD style and visibility fields validated. The original
log did not retain the rejected notification, so its exact envelope cannot be
recovered retrospectively.

Unzoned windows have no area. Core now omits their `areaId`, and canonical IPC
0.15 schema commit `d44126a0862367c4be2d4227fd9bd2068b0efb8e` permits that omission.
This shell vendors that exact correction. Supplied area IDs must still be valid;
older protocol pins remain unchanged. Core handles older peers by omitting
unzoned mount-instance metadata from their projection.

A complete invalid JSON/schema frame is now discarded without closing the core
connection. The bridge requests one fresh snapshot, ignores intervening deltas,
and retries invalid/timed-out snapshots with exponential backoff (250 ms to 5 s).
Diagnostics report method, deepest schema path, validation rule, cumulative count
and a bounded redacted shape. String values and unknown property names are never
logged; bursts emit at most one diagnostic every five seconds. Diagnostics stay
in launcher logs, outside QML. Unknown framing boundaries still require reconnect.

Reconnect uses core's renewed launcher contract: `HYPRUNE_TOKEN_REFRESH=1`, with
`renew\n` over an inherited duplex `HYPRUNE_TOKEN_FD`, followed by a fresh one-use
token. Core checks the requesting bridge PID/UID and installs the grant before
replying. Shell bounds the wait to ten seconds. Tokens never enter QML, command
arguments, files or diagnostics. Recovery requires the updated core launcher;
already-running one-shot supervisors cannot acquire this ability retroactively.

## Verification

100 shell unit tests pass, including bad deltas, repeated invalid snapshots,
malformed complete JSON, bounded/redacted diagnostics and the corrected mount
contract. The real-core nested acceptance uses the launcher and its actual
credential broker under `flock /tmp/worldshell-nested.lock`:

```sh
HYPRUNE_RECOVERY_WORLD=/path/to/local/styled-visibility-package \
  flock /tmp/worldshell-nested.lock python3 dev/recovery-core.py
```

The test warps from Lumen Reach to a local format-0.5 package with a HUD style and
visibility regions, injects an invalid delta and forces two socket disconnects. It asserts same-session
snapshot recovery, fresh authentication, restored HUD lease and no QML errors.
The test-only launcher preserves the actual bridge PID and inherited token FD;
production exposes no fault-injection endpoint.

By default the nested test now generates the generic core visibility fixture with
a HUD style; `HYPRUNE_RECOVERY_WORLD` may name a local package instead. No
identifiers, assets or captures from such a package are retained in this repository.
Redacted results are in [bridge-recovery.json](evidence/bridge-recovery.json).
The host compositor was never controlled or restarted.

With the final 0.15 schema pin, the nested run adopts two real clients on the
unbound world workspace and mounts one per world with tool-5 placement. After
each warp, after invalid-frame snapshot recovery and after each of two forced
disconnects, the received state carries nonempty mount instances whose areaId is
omitted (never empty). No reconnect or invalid frame occurs through the warps;
the injected delta is the only quarantined frame. A test-only observer in
`dev/recovery-launch.py` records counts only.
