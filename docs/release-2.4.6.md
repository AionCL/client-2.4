# Client 2.4.6 — server selection label

The server with ID 1 is displayed as `AionCL 2.4` in FRA, ENG, DEU and RUS.
The published FRA/ENG/DEU resources still called it `QA1 Server 1`.
The previous attempted rename was not located in the available launcher journal.
In-game confirmation remains required; archive validation does not prove the
Windows UI result.

## Distribution invariant

Keep the clean base client packages unchanged. Every correction or enhancement
must be a separate patch package applied after the base and existing patches.
This release appends `aioncl-client-2.4.6-018.zip` to the complete 2.4.5 manifest.
All 17 prior package descriptors, hashes and URLs remain exactly unchanged.
The current launcher resolves overlapping paths to the last package.
No launcher binary or game server change is needed.

The patch contains only the four localized `data.pak` files. Each is sourced
from its effective published 2.4.5 manifest entry and SHA-256 checked before
editing. Within each PAK only `ui/serverlist.xml` changes (case preserved).
The binary XML string table is extended and only the name reference of server
ID 1 is replaced. Other servers and all other archive entries remain unchanged.
No whitespace padding, executable patch or loose XML override is used.

## Reproduction and validation

`tools/package-server-name.py` takes `--manifest`, `--client`, `--codec`,
`--output` and `--version 2.4.6`. `--client` contains the four effective PAKs
extracted from the existing release ZIPs with their manifest paths preserved.
`--output` must be a new directory. It produces the additive ZIP, full manifest
and SHA256SUMS; it never modifies inputs or existing packages.

`--codec` is the existing `util/pak2zip/pak2zip.py` from
https://github.com/xan105/Aion-Japanese-Voice-Pack at commit
`9713427029752c2c847f1f02bca67ae36f3bba16` (pak2zip 0.4, roxfan).
Its SHA-256 must be
`5a7389756a81b1481a3e23321d6b19434e2495ea69979924b20999d145a15188`.
Only XOR table literals are read; this Python 2 script is never executed.

Run `python3 tools/test-package-server-name.py`. The builder also verifies
binary XML roundtrips, exact ID targeting, every repacked PAK entry, ZIP CRCs,
package extraction equality and preservation of all previous descriptors.

## Windows recipe

Close the game, let the launcher update `D:/games/aioncl-recette` to 2.4.6,
then log in. Confirm `AionCL 2.4` at server selection and enter the existing
character normally. Run Verify/Repair and confirm it does not restore the old
label. FRA is the reported case; ENG, DEU and RUS use the same correction.
