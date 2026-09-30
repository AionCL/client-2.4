# Client 2.4.9 — account Siel energy packs

Three gold-icon packs can be used at every playable level:

| Item ID | Duration | Name string ID |
| --- | --- | --- |
| 169700011 | 1 elapsed day | 799902 |
| 169700012 | 7 elapsed days | 799904 |
| 169700010 | 30 elapsed days | 799900 |

The existing production monthly ID remains monthly. The original client had
incorrect one-day text and a level-45 ceiling for this ID. New IDs clone its
native icon and normal quality. All three have class minimum 1, no class maximum,
no inventory expiry, stack limit 100 and localized account-wide descriptions.
Activation extends remaining account energy; time continues while offline.
Descriptions use IDs 799900–799905 in FRA/ENG/DEU/RUS.

`tools/package-siel-energy.py` starts from the exact published 2.4.8 manifest,
verifies effective source hashes, and adds one package containing
`data/items/items.pak` plus the four locale data PAKs. Inside these archives,
only `client_items.xml` and `strings/client_strings_item2.xml` change. All other
archive entries and earlier manifest packages are verified unchanged. This
preserves server-list and shop-widget fixes from 2.4.6/2.4.7.

Validation: `python tools/test-package-siel-energy.py` covers unrestricted
metadata, gold-icon preservation, elapsed durations, localized texts, unrelated
item preservation and collision rejection. The package builder checks archive
roundtrips and hashes. Actual Windows acceptance requires updating through the
launcher and checking all three items above level 50, their tooltips, activation,
remaining time, and persistence after reconnecting.
