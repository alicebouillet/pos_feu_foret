# Inventaire des fichiers

Ce document recense les fichiers suivis du dépôt et résume leur rôle. Les
fichiers de cache Python sont également listés, mais ne sont pas du code source.

## Vue d'ensemble

Le dépôt contient deux interfaces Streamlit pour comparer des scénarios de
propagation de feux de forêt, un moteur de simulation partagé sous deux chemins,
et un pipeline SIG distinct pour calculer des indicateurs de végétation autour
de bâtiments.

## Fichiers à la racine

| Fichier | Rôle |
|---|---|
| [`README.md`](README.md) | Présente l'objectif du projet : estimer le risque de feu par zone géographique en combinant aléa, enjeu et vulnérabilité. |
| [`app_feu_v2.py`](app_feu_v2.py) | Interface Streamlit principale. Permet de choisir un territoire synthétique, un relief et deux scénarios de vent, puis compare les indicateurs et les cartes d'aléa et de risque. |
| [`moteur_feu_v2.py`](moteur_feu_v2.py) | Moteur de calcul utilisé par l'interface principale : génération des territoires et reliefs, propagation stochastique sur une grille, simulations Monte-Carlo, calculs d'aléa, d'enjeu et de risque, et diagnostics de régime. |
| [`pipeline_vulnerabilite.py`](pipeline_vulnerabilite.py) | Pipeline géospatial expérimental pour une commune : sélection des bâtiments résidentiels, création de couronnes autour des bâtiments, téléchargement d'orthophotos WMS, calcul d'un masque et d'indicateurs de végétation, et génération de vignettes de toitures. Attend notamment une base BD TOPO fournie séparément. |
| [`INVENTAIRE_FICHIERS.md`](INVENTAIRE_FICHIERS.md) | Présent document : inventaire et description des fichiers du dépôt. |

## Répertoire `modele_basique/`

| Fichier | Rôle |
|---|---|
| [`modele_basique/app_feu.py`](modele_basique/app_feu.py) | Variante Streamlit de l'interface. Compare deux scénarios de vent sur les territoires synthétiques et affiche des cartes, des indicateurs et un guide présentant les hypothèses du modèle. Cette interface ne propose pas les réglages de relief de `app_feu_v2.py`. |
| [`modele_basique/moteur_feu.py`](modele_basique/moteur_feu.py) | Copie du moteur de simulation présent à la racine. L'interface de ce répertoire l'importe sous le nom `moteur_feu`. |
| [`modele_basique/requirements.txt`](modele_basique/requirements.txt) | Liste des dépendances Python déclarées pour cette variante : `matplotlib`, `numpy` et `streamlit`. `dataclasses` fait partie de la bibliothèque standard pour les versions modernes de Python. |

## Cache Python

Les fichiers ci-dessous sont des bytecodes compilés (`.pyc`) placés dans
`__pycache__/`. Ils sont produits par Python et ne sont pas destinés à être
modifiés à la main ; ils peuvent être régénérés à partir des fichiers source.

| Fichier | Source associée |
|---|---|
| [`__pycache__/app_feu.cpython-314.pyc`](__pycache__/app_feu.cpython-314.pyc) | Bytecode de `modele_basique/app_feu.py`. |
| [`__pycache__/moteur_feu.cpython-314.pyc`](__pycache__/moteur_feu.cpython-314.pyc) | Bytecode de `modele_basique/moteur_feu.py`. |
| [`__pycache__/moteur_feu_v2.cpython-314.pyc`](__pycache__/moteur_feu_v2.cpython-314.pyc) | Bytecode de `moteur_feu_v2.py`. |

## Lancement et données nécessaires

- Interface principale : `streamlit run app_feu_v2.py`
- Interface de `modele_basique/` : `streamlit run modele_basique/app_feu.py`
- Pipeline de vulnérabilité : `python pipeline_vulnerabilite.py`

Le pipeline de vulnérabilité requiert des bibliothèques géospatiales qui ne sont
pas déclarées dans `modele_basique/requirements.txt`, ainsi qu'un fichier BD TOPO
configuré dans le script. Il crée ses résultats dans un répertoire
`sortie_<commune>/` : ces données de sortie ne sont pas des fichiers source du
dépôt.
