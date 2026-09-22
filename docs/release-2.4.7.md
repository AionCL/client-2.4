# Client 2.4.7 — remove the remaining Aion shop icon

User acceptance of launcher 2.5.42 confirmed that Luna/Quna disappeared and
Aion's shop no longer opened, but its gift icon remained on the radar. This
patch suppresses that remaining visual and its clickable rectangle. Keep the
native shop disable policy in launcher 2.5.42; no new launcher binary is needed.

Each of FRA, ENG, DEU and RUS receives its effective 2.4.6 `data.pak` with
exactly three entries changed:

- `ui/game_hud_s1/radar_dialog.xml`: `item_shop` and `item_shop_bg`.
- `ui/game_hud_s2/radar_dialog.xml`: the same two widgets.
- `ui/game/player_info_dialog.xml`: secondary `btn_web_shop` access.

Names and concrete widget types remain intact because Game.dll retains native
pointers to them. Their preset, skin, effect, tooltip and other visual fields
are removed, their frame becomes `-10000,-10000,0,0`, and native flags disable
visibility, activity, input and focus. They cannot render the gift icon or
provide a clickable rectangle even if the engine later toggles visibility.
The s3 radar contains no matching shop widgets and remains byte-identical.
No shared textures, Luna controls, merchants or player personal shops change.
There is no external browser redirection; removing the visual is the preferred
user request and does not require restoring a native shop handler.

## Distribution and validation

`tools/package-shop-icons.py` uses the existing additive package builder from
`package-server-name.py` and its pinned PAK codec (same SHA requirement as 2.4.6).
It verifies each source against the effective published manifest before editing.
All 18 previous package descriptors, hashes and URLs remain unchanged.
The new package is `aioncl-client-2.4.7-019.zip`; it contains four localized PAKs.
The 2.4.6 server label, camera patch, and all other entries remain byte-identical.

Reproduce with `--manifest`, `--client`, `--codec`, `--output`, and
`--version 2.4.7`. Output must be new. The source client is never modified.
The binary XML parser supports attributes and preserves the original string
table. Input and output XML roundtrip, exact widget count/type, unrelated-node
identity, every repacked PAK entry, ZIP CRC/extraction, and prior package
preservation are checked. Run `python3 tools/test-package-shop-icons.py` and
`python3 tools/test-package-server-name.py` for regression coverage.

## Windows acceptance

Close Aion and update the client through launcher 2.5.42 or later on
`D:/games/aioncl-recette`. Enter the existing character and confirm that the
gift/shop icon and its border are absent with no invisible clickable hotspot.
Luna must remain absent. Check the other radar controls and a normal merchant.
If using both HUD layouts, check both; then Verify/Repair and restart to confirm
that the icon does not return. Visual acceptance requires the actual game and
is not claimed by the structural packaging checks.

## User acceptance confirmed — 2026-09-22

Aymen confirmed: « Parfait c'est bien supprimé maintenant ». Removal of the
remaining Aion shop icon is visually accepted after client 2.4.7. The earlier
feedback already confirmed Luna/Quna removal and the inactive Aion shop.
The reported issue is resolved. Separate checks of all languages/HUD layouts,
merchants, shortcuts and Verify/Repair were not explicitly reported.
