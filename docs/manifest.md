# Contrat du manifest, formatVersion 1

`install-manifest.json` est un JSON UTF-8 sans BOM. Tous les nombres de taille sont des entiers en octets (utiliser des entiers 64 bits côté launcher). Les SHA-256 sont hexadécimaux, sur 64 caractères minuscules.

| Champ | Signification |
| --- | --- |
| `formatVersion` | Version du contrat : `1`. Refuser une version inconnue. |
| `product`, `gameVersion` | `AionCL`, `2.4`. |
| `clientVersion` | Version du lot, initialement `2.4.0`. |
| `buildId` | SHA-256 des entrées de construction : inventaire trié, version, limite, URL et convention de compression. Ce n'est pas une signature. |
| `archiveFormat` | `zip`, archives indépendantes, DEFLATE. ZIP64 peut être utilisé. |
| `maxPackageBytes` | Plafond inclusif par archive, strictement inférieur à 2 GiB. |
| `sourceFileCount`, `sourceBytes` | Nombre et taille totale des fichiers sélectionnés après exclusions. |
| `compressedBytes` | Somme des tailles des ZIP, hors manifest et SHA256SUMS. |
| `packages` | Tableau ordonné, au moins une archive. |
| `packages[].name` | Nom unique au format `aioncl-client-2.4.N-001.zip`. Une mise à jour peut réutiliser un ZIP inchangé d’une version précédente ; le nom et l’URL restent alors ceux de cette version précédente. |
| `packages[].size`, `sha256` | Taille et hash du ZIP téléchargé. |
| `packages[].fileCount`, `uncompressedSize` | Nombre et taille totale des fichiers du ZIP. |
| `packages[].mirrors` | Tableau d'URL HTTPS. Vide dans un build local sans `BaseUrl`. |
| `packages[].files` | Inventaire exact du ZIP : objets `path`, `size`, `sha256`. |

Les chemins `files[].path` sont relatifs à la racine d'installation, avec `/`, sans répertoire parent englobant. Aucun fichier ne figure dans plusieurs packages. Les répertoires vides, ACL, flux NTFS alternatifs et dates originales ne sont pas distribués. Les liens symboliques/jonctions sélectionnés sont refusés. Les noms incompatibles avec Windows et les collisions de casse sont refusés.

## Procédure du futur launcher

1. Charger un manifest obtenu via une source HTTPS de confiance ; vérifier le contrat, les compteurs et les chemins. `SHA256SUMS` contrôle aussi le manifest, mais ne remplace pas une signature ou un canal de confiance.
2. Pour chaque package, télécharger depuis `mirrors`, ou résoudre `name` relativement à une URL de distribution configurée. Si les deux manquent, refuser l'installation réseau avec une erreur explicite. Le build local est utilisable hors ligne.
3. Vérifier taille et SHA-256 de chaque ZIP avant extraction. Les ZIP sont autonomes : aucune concaténation de volumes.
4. Extraire dans un répertoire de préparation contrôlé. Rejeter les chemins absolus, `..`, liens, collisions et entrées absentes de l'inventaire. Ne jamais extraire à travers une jonction existante.
5. Vérifier taille et SHA-256 des fichiers extraits, puis finaliser l'installation. Ne pas supprimer des fichiers utilisateur simplement parce qu'ils ne figurent pas au manifest.

`Test-Packages.ps1 -Deep` vérifie l'ensemble de l'inventaire par lecture décompressée, sans extraction sur disque. Le code de sortie PowerShell est non nul en cas d'erreur lorsque le script est exécuté avec `powershell.exe -File`.

Le format prépare l'installation complète ; il ne définit pas encore les mises à jour différentielles, la configuration du serveur, la signature du manifest ou le lancement du jeu.
