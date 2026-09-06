# AionCL — Distribution du client 2.4

Scripts PowerShell de préparation et de vérification des archives d'installation.

## Prérequis

Windows PowerShell 5.1 avec .NET Framework 4.7.2 ou ultérieur, ou PowerShell 7 sous Windows. Aucun outil de compression externe n'est nécessaire.

## Génération

Depuis la racine du dépôt, fournir le chemin de la source :

```powershell
.\scripts\Build-Packages.ps1 -SourcePath '<dossier-source>'
```

La version, le plafond des archives et les exclusions sont définis dans `config/packaging.json`. Les ZIP indépendants, le manifest et `SHA256SUMS` sont produits dans `artifacts/v<version>/`, ignoré par Git. La taille maximale par archive est de 1 800 000 000 octets.

Paramètres facultatifs :

- `-OutputRoot` : répertoire de sortie, séparé de la source.
- `-ConfigPath` : configuration alternative ; conserver les réglages locaux dans `.local/`.
- `-BaseUrl` : URL HTTPS publique du répertoire de téléchargement. Sans ce paramètre, les miroirs du manifest sont vides.

Fermer le jeu et les outils modifiant la source pendant la génération. Prévoir sur le volume de sortie au moins la taille de la source plus 10 % de marge. Les exclusions sont des motifs PowerShell appliqués aux chemins relatifs avec `/` ; les examiner avant de préparer une distribution.

La génération vérifie les hashes des archives et de tous leurs fichiers avant de finaliser le lot. Une relance avec les mêmes entrées vérifie et réutilise le lot existant. Si les entrées changent, choisir une nouvelle version ou une autre sortie. Un fichier trop volumineux pour un ZIP est refusé explicitement.

## Vérification

```powershell
.\scripts\Test-Packages.ps1 -ManifestPath '<dossier-du-lot>\install-manifest.json' -Deep
.\scripts\Test-Packaging.ps1
```

`-Deep` contrôle aussi chaque fichier décompressé. Sans cette option, le contrôle porte sur les hashes des archives et du manifest ainsi que sur la cohérence des métadonnées. Les tests synthétiques produisent leurs données dans `.local/`.

Le [contrat du manifest](docs/manifest.md) décrit les données destinées au launcher. Pour une distribution, les ZIP, le manifest et `SHA256SUMS` doivent être placés au même emplacement de téléchargement.

## Fichiers versionnés

Seuls ce README, les règles Git, la configuration générique, les scripts et le contrat du manifest sont autorisés par `.gitignore`. Tout nouveau fichier à versionner doit être ajouté explicitement à cette liste après examen. Les builds, inventaires générés, notes et configurations personnelles restent locaux.
