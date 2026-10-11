# Adventure / Placement HUD contract

Adventure replaces the earlier default concept; Instrument and Minimal keep their
layouts. Saved choices of the earlier concept migrate without resetting curvature,
resources or world styles.
Legacy `ui.hud.cycle` events are ignored. Selection is Settings/config only.

IPC 0.15 `editor.unplaced` supplies count, ordered window rows, selectedId and
preview. App icon names come from `state.apps`; title/class/logicalSize come from
the selected queue row. No thumbnails are published, so shell uses a theme icon.
The four tool tiles become one larger original window-placement glyph. The
adjacent card displays the selected app, dimensions and pocket position/count;
a count badge appears outside Placement. Core owns initial selection (5 when
the pocket is nonempty) and mouse behavior. Shell sends no inferred tool changes.

Tool hints use `editor.toolSlots` for all five tools: Primary, Secondary,
Alternate and Cycle labels are supplied by core, with bindings from the live
keymap. Null slots are omitted and explicit empty bindings read Unbound. Help
uses `editor.toolDefinitions`. The default Placement mapping is **Wheel cycle ·
LMB place ahead · RMB on surface · MMB pocket**; none of these labels or bindings
is a per-tool HUD string. There is no return-to-last-spot operation.
A successful `placement.pocketed` notice becomes
a brief title-bearing centre banner, not an inferred queue-arrival event.

`editor.toolInput` publishes modifier state, the override flag and eligible
`gestures:[{action,label,bindings}]`. While overridden, these replace the tool
slots under GLOBAL GESTURES. On release the ordinary slots return; carry-facing
remains available during a carry. The shell does not capture modifier keys or
infer gesture eligibility. All binding strings come from core, including remaps.

`editor.carryFacing` is nullable; true/false yields FACING YOU / KEEP ANGLE with
the current `carry.facing` binding. `editor.contentScale` provides scale, requested
logicalSize and sequence/reset. A changed sequence shows a 2.4 s readout; repeated
resets at 100% show RESET again. Reconnect baselines do not replay old feedback.
Free-cursor mode suppresses actionable placement/carry/scale prompts.

A loaded world plus inactive runtime produces a transient readiness notification;
`runtime.ready`, when published, replaces fallback wording with core's toggle
hint. The notification is passive and styled by the selected concept. Returning
to the desktop does not repeatedly announce the same loaded world.
