# Client 2.4.10 — tradable Siel energy packs

All three packs (169700011: 1 day, 169700012: 7 days, 169700010: 30 days)
are ordinary consumables that allow player exchange, broker/personal-store
sale, NPC sale, character/account/legion storage, dropping and stack splitting.
They remain unbound and unrestricted by level.

Native cash/recharge metadata is zeroed (`cash_item`, `cash_available_minute`)
to remove the obsolete ticket/double-time confirmation. Activation remains
Both/count 1; the server applies and persists the account duration using the
item ID. Names, descriptions, icons and durations are unchanged.

The additive package modifies only `data/items/items.pak` / `client_items.xml`.
All other archive entries and all prior manifest packages are verified unchanged.
`tools/test-package-siel-trading.py` verifies flags, disabled native recharge,
continued activation, names/icons and missing-pack rejection. Actual in-game
acceptance must verify direct use, exchange, broker listing and personal-store
listing for all three durations after updating through the launcher.
