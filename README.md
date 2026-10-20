# POS — Risque de feux de forêt

Projet de recherche autour de l'estimation du risque de feu à l'échelle d'un
territoire. Le dépôt contient un prototype de simulation sur grille et un
pipeline géospatial expérimental destiné à caractériser la végétation autour des
bâtiments.

> **Limite d'usage :** les cartes et chiffres de l'interface sont issus de
> territoires synthétiques et d'un modèle simplifié. Ils ne constituent pas des
> prévisions opérationnelles ni une évaluation calibrée pour un territoire réel.

## Fonctionnalités

L'interface principale permet de :

- choisir l'un des territoires synthétiques (lisière forêt/lande, hameau en
  forêt ou maisons en bord de route) et ses dimensions ;
- choisir une forme de relief et régler sa pente ;
- comparer deux scénarios de vent avec les mêmes points de départ et les mêmes
  flux aléatoires, afin de rendre leur différence plus directement comparable ;
- visualiser les cartes d'aléa et de risque, les surfaces brûlées simulées et
  des diagnostics de propagation.

Le moteur représente le territoire par une grille de cellules de 50 m. Le feu se
propage de manière stochastique vers les quatre cellules cardinales. La
probabilité de propagation dépend du combustible, du vent et, dans la version
principale, de la pente. L'aléa est estimé par simulations de Monte-Carlo. Le
risque est calculé à partir de l'aléa, du nombre de maisons, d'une valeur
conventionnelle par maison et d'un facteur de vulnérabilité constant.

## Démarrage rapide

Prérequis : Python 3.10 ou supérieur et `pip`.

Depuis la racine du dépôt, installez les dépendances utilisées par l'interface :

```bash
python -m pip install numpy matplotlib streamlit
```

Lancez ensuite l'interface principale :

```bash
streamlit run interface_risque_avec_relief.py
```

Streamlit affiche l'adresse locale de l'application dans le terminal (en général
`http://localhost:8501`).

## Variantes de l'interface

### Interface principale — relief

```bash
streamlit run interface_risque_avec_relief.py
```

Utilise [`moteur_simulation_feu.py`](moteur_simulation_feu.py). Elle inclut le
choix du relief (terrain plat, versant, vallée ou colline) et son effet sur la
propagation.

### Interface basique — vent

```bash
streamlit run modele_sans_relief/interface_risque.py
```

Utilise [`modele_sans_relief/moteur_simulation.py`](modele_sans_relief/moteur_simulation.py). Elle
propose une présentation guidée du modèle et compare les effets du vent, sans
réglage du relief. Les dépendances de cette variante sont listées dans
[`modele_sans_relief/requirements.txt`](modele_sans_relief/requirements.txt).

## Pipeline de vulnérabilité du bâti

[`pipeline_vegetation_batiments.py`](pipeline_vegetation_batiments.py) est un traitement SIG
distinct de la simulation sur grille. Il sélectionne les bâtiments résidentiels
d'une commune dans une base BD TOPO, crée des couronnes autour des emprises,
télécharge des orthophotos IRC/RVB depuis le service WMS de la Géoplateforme,
calcule des indicateurs de végétation et produit un échantillon de vignettes de
toitures.

Le script nécessite une base BD TOPO au format GeoPackage et des dépendances
géospatiales. Le chemin de la base, la commune et les paramètres de traitement
sont configurés au début du script. Les dépendances indiquées par le script
peuvent être installées avec :

```bash
python -m pip install geopandas pyogrio rasterio rasterstats requests pillow numpy shapely
```

Puis lancez :

```bash
python pipeline_vegetation_batiments.py
```

Le traitement écrit ses résultats dans `sortie_<commune>/` (GeoPackages,
rasters, CSV et images). Il nécessite un accès réseau pour les requêtes WMS.

## Organisation du dépôt

- [`interface_risque_avec_relief.py`](interface_risque_avec_relief.py) : interface Streamlit principale avec relief.
- [`moteur_simulation_feu.py`](moteur_simulation_feu.py) : modèle de propagation et calcul du
  risque utilisé par l'interface principale.
- [`modele_sans_relief/`](modele_sans_relief/) : variante d'interface et moteur
  sans relief.
- [`pipeline_vegetation_batiments.py`](pipeline_vegetation_batiments.py) : pipeline de
  caractérisation géospatiale de la végétation autour des bâtiments.
- [`INVENTAIRE_FICHIERS.md`](INVENTAIRE_FICHIERS.md) : description plus détaillée
  des fichiers du dépôt.

## Hypothèses et limites du modèle

- Les territoires, les maisons et les départs de feu sont synthétiques.
- Le vent est uniforme et constant pendant chaque simulation.
- Le feu ne se propage qu'aux quatre voisines cardinales ; les sautes de feu et
  l'intervention des secours ne sont pas représentées.
- Le nombre de départs annuels, la valeur d'une maison et la vulnérabilité sont
  des paramètres fixes du moteur.
- Le facteur d'humidité est actuellement neutre (égal à 1) : l'humidité n'a pas
  d'effet dans le modèle à ce stade.
- Le pipeline SIG calcule des indicateurs autour des bâtiments, mais n'est pas
  encore intégré au modèle de risque de l'interface.

Les résultats doivent donc être interprétés comme des sorties exploratoires
permettant de comparer des scénarios au sein de ce prototype, et non comme une
mesure absolue du risque réel.

## Anciens chemins conservés

Les anciens chemins du pipeline SIG et de la variante sans relief sont
conservés comme relais de compatibilité. Les anciens chemins de l'interface
principale et de son moteur ont été supprimés ; utilisez les noms explicites
présentés dans ce README.
