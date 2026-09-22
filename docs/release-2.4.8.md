# Client 2.4.8 — suppress obsolete mixed-faction merge warning

AionCL allows Elyos and Asmodian characters on the same account and server.
The server-side S_VERSION_CHECK fix enables this behavior, but the original
Aion Classic 2.4 client still displays an obsolete Gameforge server-merge
warning when both factions are present.

This release suppresses that historical warning without changing the
mixed-faction permission itself.

## Game.dll patch

Supported original Game.dll:

- size: 22377856 bytes
- SHA-256: `f259b60f74768c226eafff085551700bcaf3aa43a20ede7fe3925e0e31daaf0f`

Patch:

- file: `bin64/Game.dll`
- file offset: `0x2C6080`
- virtual address: `0x1802C6080`
- original bytes: `8B 05 1A 67 BC 00`
- patched bytes: `E9 7D 01 00 00 90`
- jump target: `0x1802C6202`

Patched Game.dll SHA-256:

`5fe3d86433122a007c9bb1b51ba6a5d380c83399a28166e3427f2d0a4a9cb9c0`

The patched branch skips the obsolete mixed-faction merge-warning block.
It does not enable mixed-faction character creation by itself; that behavior
depends on the corresponding server-side S_VERSION_CHECK fix.

## Distribution

`tools/package-mixed-faction.py` verifies the effective Game.dll from the
published manifest, requires the exact supported source SHA-256 and original
instruction bytes, applies the patch, verifies the known-good resulting
SHA-256, and creates one additive package.

All previous packages remain unchanged. The new package contains only:

`bin64/Game.dll`

## Validation

`tools/test-package-mixed-faction.py` verifies the exact patch offset,
original bytes and generated jump encoding, and rejects unsupported input.

The resulting Game.dll was also tested in the real Windows AionCL client.
Mixed Elyos/Asmodian character selection continued to work and the obsolete
server-merge warning no longer appeared.
