# Boutique : première mise à jour incrémentale

La révision `2.4.1` réutilise les onze ZIP inchangés de `v2.4.0` et remplace
seulement les packages `002`, `003` et `004`, qui contiennent respectivement
les PAK DEU, ENG et FRA. Le manifest `2.4.1` reste complet : les packages
réutilisés gardent leur nom et leur URL `v2.4.0`, tandis que les trois packages
corrigés portent un nom `v2.4.1` et une URL de la release corrective.

Les PAK corrigés doivent d'abord être générés par
`website/tools/patch_client_shop_urls.py` depuis les PAK originaux, puis
validés par son round-trip. `tools/repack-shop-packages.py` remplace exactement
l'entrée `l10n/<lang>/data/data.pak` dans chaque ZIP original. Il ne modifie
jamais les ZIP ou le client source.

Le launcher compare ensuite le manifest complet à l'installation existante.
Les onze packages inchangés sont déjà valides et ne sont pas téléchargés ; les
trois packages corrigés sont téléchargés, extraits et vérifiés.
