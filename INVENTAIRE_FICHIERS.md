# Inventaire des fichiers

Ce document recense les fichiers suivis du dépôt et résume leur rôle. Les noms
principaux sont descriptifs ; les anciens chemins sont maintenus uniquement
pour la compatibilité.

## Vue d'ensemble

Le dépôt contient deux interfaces Streamlit de comparaison de scénarios de feu,
deux moteurs de simulation (la variante principale prend en compte le relief) et
un pipeline SIG distinct pour caractériser la végétation autour des bâtiments.

## Fichiers à la racine

| Fichier | Rôle |
|---|---|
| [`README.md`](README.md) | Présente le projet, les installations, les lancements et les limites du modèle. |
| [`interface_risque_avec_relief.py`](interface_risque_avec_relief.py) | Interface Streamlit principale : choix du territoire synthétique, du relief et de deux scénarios de vent, comparaison des indicateurs et affichage des cartes. |
| [`moteur_simulation_feu.py`](moteur_simulation_feu.py) | Moteur principal : génération des territoires et reliefs, propagation stochastique, simulations Monte-Carlo et calcul de l'aléa et du risque. |
| [`pipeline_vegetation_batiments.py`](pipeline_vegetation_batiments.py) | Pipeline SIG expérimental : bâtiments résidentiels, couronnes, orthophotos, indicateurs de végétation et vignettes de toitures. Nécessite une base BD TOPO fournie séparément. |
| [`INVENTAIRE_FICHIERS.md`](INVENTAIRE_FICHIERS.md) | Présent document : inventaire des fichiers et explication de leur rôle. |

## Répertoire `modele_sans_relief/`

| Fichier | Rôle |
|---|---|
| [`modele_sans_relief/interface_risque.py`](modele_sans_relief/interface_risque.py) | Variante Streamlit sans réglage du relief, avec guide de prise en main et explication des hypothèses. |
| [`modele_sans_relief/moteur_simulation.py`](modele_sans_relief/moteur_simulation.py) | Moteur de simulation utilisé par la variante sans relief. |
| [`modele_sans_relief/requirements.txt`](modele_sans_relief/requirements.txt) | Dépendances de cette variante : `matplotlib`, `numpy` et `streamlit`. |


## Cache Python

Les fichiers compilés présents dans `__pycache__/` sont des bytecodes Python
générés, et non des sources à modifier. Ils ne sont pas nécessaires au lancement
et Python peut les régénérer.

## Lancement et données nécessaires

- Interface principale : `streamlit run interface_risque_avec_relief.py`
- Interface sans relief : `streamlit run modele_sans_relief/interface_risque.py`
- Pipeline SIG : `python pipeline_vegetation_batiments.py`

Le pipeline SIG requiert des bibliothèques géospatiales qui ne sont pas listées
dans `modele_sans_relief/requirements.txt`, ainsi qu'une base BD TOPO configurée
dans le script. Il crée les résultats dans `sortie_<commune>/` ; ces données ne
sont pas des fichiers source du dépôt.
