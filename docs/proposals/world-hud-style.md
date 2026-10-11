# World HUD styles — reconciled shell format

**Authoring decision:** use the version 1 format below. The v0.1 author proposal is retained for rationale; its field names are superseded by the final mapping.

## Author proposal (received)

A data-only world may declare `extensions["com.hyprune.hud-style"] = {"version":"0.1","path":"hud/theme.json"}`. Unknown optional metadata is ignored. Paths in the style resolve from the immutable package root. Shell applies a validated style atomically after world readiness, restores defaults on exit, and rolls back on failed warp. No world identity or third-party reference art is required by this proposal.

Theme schema: `formatVersion`, `id`, `name`, semantic `colors` (background, foreground, outline, panel, accent, secondary, muted, focus, danger, selection, onAccent); `typography` (local family/path/license/fallback, scale, minimumSizePx); `stroke` (color,widthPx,linecap,linejoin); `shape` (cornerRadiusPx,cornerStyle,shadowOffsetPx,shadowColor); `icons` (fixed semantic roles to local SVG paths); bounded `motion`; optional `areaAccents` keyed by area ID. Colors are sRGB hex; pixel dimensions are logical screen pixels. Live application contents retain their own appearance. User font, contrast, motion and scale preferences always override world values.

Bound to 32 KiB JSON, 16 local SVGs of 16 KiB/128 paths each, one font of 1 MiB, and 32 area accents. Safe SVG primitives only: no scripts, event handlers, external references, animation, filters, use, text or foreignObject. Reject path traversal/symlinks/URLs. Stroke 1–4px; radius 0–16px; text scale .9–1.2; enforce contrast and a readable minimum size. Missing/invalid assets fall back per role with one diagnostic. Cache by package digest and discard at world exit.

A related optional warp style could supply a named bounded built-in effect plus colors, a local icon and timing. Example: an ink-edged oval portal expands after `world.ready`, then fades on completion; loading remains indeterminate, failure leaves the previous world intact. Reduced motion uses a short dissolve. Worlds cannot change camera pose, input capture, actual progress or activation timing. Prefer a built-in shell renderer over package-authored animation instructions.

Acceptance: two installed worlds swap themes without leaking styles; rejected/missing themes and failed warp preserve usable HUD; offline assets only; accessibility overrides win; compositor/application pixels stay unchanged. The implementation should expose the applied theme ID/version in diagnostics. This is a proposal, not a claim of current shell support.

## Final version 1 authoring contract

Manifest (optional extension; never add to requiredExtensions):

```json
{"extensions":{"com.hyprune.hud-style":{"theme":"hud/theme.json"}}}
```

Theme example:

```json
{
  "version": 1,
  "colors": {
    "accent": "#ffd28a", "foreground": "#fff4dc", "muted": "#dcccb2",
    "tile": "#745021", "outline": "#16100b", "scrim": "#21170c"
  },
  "stroke": {"width": 2, "style": "outline"},
  "corners": "round",
  "font": "hud/fonts/Display.ttf",
  "icons": {"navigate":"hud/icons/navigate.svg", "window":"hud/icons/window.svg"},
  "warp": "ribbons"
}
```

Only `version` is required. Missing values inherit the selected concept.
Colors are opaque six-digit hex. Stroke width 1–3 applies to native glyphs.
Text defaults to solid fill with a soft dark shadow (50% opacity, small offset).
An explicit `stroke.style: "outline"` selects a native one-pixel text outline;
`shadow` or an omitted stroke style uses the soft shadow, independent of custom art.
`style`: outline or shadow. Corners: square, bevel, round. Warp: default,
ribbons, soft. Icons: navigate, window, path, position. Subtype glyphs remain
original semantic art; overrides must not change tool names or actions.
Font is an optional packaged TTF/OTF, loaded by Qt only from the shell's private
validated asset cache; fallback is the built-in font. No system-font aliases,
network URLs or package-external files are accepted.

Canonical proposed schemas: `schema/extensions/hud-style.schema.json` and
`hud-style-manifest.schema.json`. Asset paths start `hud/`, contain only safe
ASCII components, and cannot contain traversal, URL schemes or symlinks.
Theme max 32 KiB; each SVG max 16 KiB / 128 elements; font max 1 MiB.
SVG uses static basic geometry, groups, gradients and local clipping only.
No scripts, event handlers, CSS, text, animation, images, foreignObject, use,
external references, declarations, entities or processing instructions.
Reject invalid theme JSON; invalid optional assets fall back per role.

Readability: foreground and secondary colors must contrast >=4.5:1 with the
opaque dark outline; accent >=3:1. Unsafe colors are replaced with defaults.
Scrims stay dark; icon tile contrast is guarded. Color changes animate for
420 ms (instant with reduced motion); assets change without geometry changes.
Director menus, focus indicators, emergency controls, cursor and world-locked
core overlays are never styled by this extension. Warp variant changes only
shell-owned decoration, preserving progress and destination text.

`Use world HUD styles` in Appearance is saved and defaults on. Opt-out restores
the selected concept immediately. Exiting/changing worlds restores base tokens
before applying another validated skin. Package discovery currently requires a
launcher-authorised `--world-package /installed/package/world.json`; the shell
selects it by authenticated active world ID. Metadata-based discovery has been
requested from core; no manifest-controlled absolute root is trusted.

Sample: `dev/styles/signal-amber/` is original warm Signal Rise-inspired art.
The nested harness installs it only into its private Lumen Reach copy.

## Reconciliation decisions

The shell implements the requested presentation surface with fixed semantic
roles and no package-controlled layout dimensions. Use `{ "theme": "hud/theme.json" }`
in the extension and integer `version: 1` in the theme; the proposed v0.1
`version/path` and `formatVersion` spellings are not accepted aliases. Map
`typography.path` to `font`, panel/background to `colors.scrim`, secondary to
`colors.muted`, shape.cornerStyle to `corners`, stroke.widthPx to stroke.width.
Keep font licensing in package attribution. Optional `id` and `name` identify
skins in diagnostics. `areaAccents`, text scaling, menu/focus/danger overrides,
world-defined timing, arbitrary shadows and custom warp icons are deferred.

Accepted asset limits use the stricter author proposal: 16 KiB and 128 nodes
per SVG, one 1 MiB TTF/OTF; four tool icon roles. Invalid optional assets fall
back per role, with one bounded diagnostic. Invalid theme JSON falls back to
the selected concept. Typography never reduces the user's text size. Built-in
warp variants preserve core's transition phases, progress and reduced motion.
