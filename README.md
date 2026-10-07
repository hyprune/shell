# Hyprune shell

The reference Quickshell shell. **Early, building in the open.**

> What if the computer itself were an explorable world?

Shell owns Quickshell UI, overlays, world selection, mode/focus indicators, notices and settings presentation. It consumes snapshots and deltas over the public Unix IPC protocol and uses per-output leases for interactive overlays.

It excludes compositor hooks, physics, window capture, permission authority and world art. It never polls a state JSON file. Alternative shells implement [RFC-0008](https://hyprune.com/rfcs/0008-shell/) without importing this repository.

First target: a small client that negotiates IPC `0.1`, shows authoritative state, reconnects cleanly and exposes a reliable desktop exit. Full interactive conformance follows the M1 methods and failure tests. No shell implementation is included in this initial repository.

## Boundaries and contracts

- [RFC-0001: umbrella architecture](https://hyprune.com/rfcs/0001-umbrella/)
- [RFC-0003: IPC `0.1`](https://hyprune.com/rfcs/0003-ipc/)
- [RFC-0004: world format `0.1`](https://hyprune.com/rfcs/0004-world-format/)
- [Machine-readable schemas and fixtures](https://github.com/hyprune/schema)
- [Roadmap M0–M3](https://hyprune.com/roadmap/)

RFCs are proposed implementation targets pending owner review. Read them now in [the docs source](https://github.com/hyprune/docs/tree/main/src/content/docs/rfcs) if the site is not deployed. Each core release must publish its exact Hyprland compatibility target and supported contract versions. Hyprune is new code; Hypr3D is a lessons-only historical reference.

## Contributing

See the [organization guide](https://github.com/hyprune/.github/blob/main/CONTRIBUTING.md) and [Code of Conduct](https://github.com/hyprune/.github/blob/main/CODE_OF_CONDUCT.md). Contract changes begin with an RFC amendment and schema fixtures. Keep provenance and failure evidence with your PR.

License: MIT; see [LICENSE](LICENSE).
