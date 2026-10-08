# World HUD style 1 — shell integration proposal

Status: implemented shell prototype; proposed RFC-0004/RFC-0008 amendment.
The personal-world proposal had not arrived when this baseline was written;
please add compatibility notes here. Layout remains the user's Vanguard,
Instrument or Minimal concept. No executable QML, JavaScript or shaders.

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
Colors are opaque six-digit hex. Stroke width 1–3 applies to native glyphs;
text keeps a native one-pixel outline/shadow, independent of custom art.
`style`: outline or shadow. Corners: square, bevel, round. Warp: default,
ribbons, soft. Icons: navigate, window, path, position. Subtype glyphs remain
original semantic art; overrides must not change tool names or actions.
Font is an optional packaged TTF/OTF, loaded by Qt only from the shell's private
validated asset cache; fallback is the built-in font. No system-font aliases,
network URLs or package-external files are accepted.

Canonical proposed schemas: `schema/extensions/hud-style.schema.json` and
`hud-style-manifest.schema.json`. Asset paths start `hud/`, contain only safe
ASCII components, and cannot contain traversal, URL schemes or symlinks.
Theme max 32 KiB; each SVG max 64 KiB / 256 elements; font max 4 MiB.
SVG uses static basic geometry, groups, gradients and local clipping only.
No scripts, event handlers, CSS, text, animation, images, foreignObject, use,
external references, declarations, entities or processing instructions.
Reject invalid files as a whole; retain the concept's style.

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
selects it by authenticated active world ID. Core metadata discovery is requested
in its SDK/shell handoff; no manifest-controlled absolute root is trusted.

Sample: `dev/styles/signal-amber/` is original warm Signal Rise-inspired art.
The nested harness installs it only into its private Lumen Reach copy.
