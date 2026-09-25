"""
POS Feux de forêt — moteur de simulation (sans interface)

Ce module contient tout le modèle : grille, propagation, automate cellulaire,
Monte-Carlo, aléa / enjeu / vulnérabilité / risque.
Il est volontairement séparé de l'interface Streamlit pour rester utilisable
depuis un notebook ou un script (figures du rapport, calibration, etc.).

Structure de la probabilité de propagation :

    p(c -> c') = min( p_k(c') * f_vent * f_pente * f_humidite , 1 )
                          ^        ^         ^         ^
                          |        |         |         `-- À IMPLÉMENTER (étape 3)
                          |        |         `------------ À IMPLÉMENTER (étape 3)
                          |        `---------------------- implémenté (étape 2)
                          `------------------------------- doc de départ (étape 1)

Les facteurs sont multiplicatifs et indépendants : en ajouter un nouveau se fait
dans `facteurs_propagation()` sans toucher au reste.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------
# Paramètres physiques / économiques (repris du doc de départ)
# ---------------------------------------------------------------------------

DELTA = 50  # côté d'une cellule, en mètres

INCOMBUSTIBLE, LANDE, FORET = 0, 1, 2
NOMS_COMBUSTIBLE = {INCOMBUSTIBLE: "incombustible", LANDE: "lande", FORET: "forêt"}
P_K = {INCOMBUSTIBLE: 0.00, LANDE: 0.25, FORET: 0.45}

LAMBDA_FEU_AN = 0.5      # départs de feu par an sur le domaine
V_MAISON = 250_000       # valeur d'une maison, en euros
VULNERABILITE = 0.6      # taux de destruction, constant dans cette version

ETAT_INTACTE, ETAT_FEU, ETAT_BRULE = 0, 1, 2

VOISINS = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # nord, sud, ouest, est

P_CRITIQUE = 0.5  # seuil de percolation de liens sur réseau carré (cf. H2)


# ---------------------------------------------------------------------------
# Vent
# ---------------------------------------------------------------------------

VITESSE_REFERENCE = 20.0  # km/h : vitesse implicite du "vent d'ouest fixe" du doc

# f(theta) = A + B cos(theta) + D cos(2 theta), calibrée pour passer exactement par
# les 3 valeurs du doc de départ : f(0°)=2.2 (sous le vent), f(90°)=1.0 (travers),
# f(180°)=0.4 (contre le vent). Ces coefficients sont l'unique solution du système.
_A, _B, _D = 1.15, 0.9, 0.15


@dataclass(frozen=True)
class Vent:
    """direction_deg : cap COMPAS vers lequel le vent souffle.
    0 = vers le nord, 90 = vers l'est, 180 = vers le sud, 270 = vers l'ouest.
    Un « vent d'ouest » (qui vient de l'ouest) souffle vers l'est : direction_deg = 90.
    """

    direction_deg: float = 90.0
    vitesse_kmh: float = VITESSE_REFERENCE


def bearing(dy: int, dx: int) -> float:
    """Cap compas du déplacement (dy, dx). dy > 0 = vers le sud (ligne suivante)."""
    return float(np.degrees(np.arctan2(dx, -dy)) % 360)


def f_vent_calibree(theta_deg: float | np.ndarray) -> float | np.ndarray:
    """Anisotropie du vent à la vitesse de référence, en fonction de l'angle
    entre la direction de propagation et celle du vent."""
    theta = np.radians(theta_deg)
    return np.maximum(_A + _B * np.cos(theta) + _D * np.cos(2 * theta), 0.01)


def facteur_vent(dy: int, dx: int, vent: Vent) -> float:
    """Généralise la table à 4 valeurs du doc : direction quelconque, vitesse variable.
    À vitesse nulle le facteur vaut 1 partout (isotrope) ; à VITESSE_REFERENCE on
    retrouve exactement 2.2 / 1.0 / 0.4."""
    theta = bearing(dy, dx) - vent.direction_deg
    return float(f_vent_calibree(theta) ** (vent.vitesse_kmh / VITESSE_REFERENCE))


# ---------------------------------------------------------------------------
# Conditions de propagation (point d'extension pour pente / humidité)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Conditions:
    """Conditions environnementales appliquées à la propagation.

    Pour l'instant seul le vent est implémenté. Les deux autres facteurs sont
    des points d'extension documentés — voir `facteurs_propagation()`.
    """

    vent: Vent = field(default_factory=Vent)


def facteur_pente(dy: int, dx: int, conditions: Conditions, cellule: tuple[int, int]) -> float:
    """À IMPLÉMENTER (étape 3).

    Le feu monte beaucoup plus vite qu'il ne descend : la flamme se rapproche du
    combustible en amont-pente, ce qui le préchauffe. Il faudra :
      1. un MNT (modèle numérique de terrain) : une grille d'altitudes z(c) ;
      2. la pente locale dans la direction de propagation, alpha = atan((z(c') - z(c)) / d) ;
      3. un facteur du type exp(a * tan(alpha)), à calibrer sur la littérature.
    Renvoie 1.0 tant que ce n'est pas fait (pas d'effet de pente).
    """
    return 1.0


def facteur_humidite(conditions: Conditions, k_recept: int) -> float:
    """À IMPLÉMENTER (étape 3).

    L'humidité du combustible (fine fuel moisture) conditionne l'inflammabilité :
    au-delà d'un seuil dit « d'extinction » (~30 % pour l'herbe), le feu ne
    passe plus du tout. Un facteur décroissant en fonction de l'humidité, dépendant
    de la classe de combustible, est à calibrer (piste : indice FWI / Rothermel).
    Renvoie 1.0 tant que ce n'est pas fait (pas d'effet d'humidité).
    """
    return 1.0


def facteurs_propagation(
    k_recept: int, dy: int, dx: int, conditions: Conditions, cellule: tuple[int, int]
) -> float:
    """Probabilité de franchissement d'une interface : produit des facteurs.
    Ajouter un nouveau facteur = ajouter un terme ici."""
    p = (
        P_K[k_recept]
        * facteur_vent(dy, dx, conditions.vent)
        * facteur_pente(dy, dx, conditions, cellule)
        * facteur_humidite(conditions, k_recept)
    )
    return min(p, 1.0)


# ---------------------------------------------------------------------------
# Scénarios de territoire
# ---------------------------------------------------------------------------

SCENARIOS = {
    "Lisière forêt / lande + hameau": "lisiere",
    "Hameau en pleine forêt": "hameau_foret",
    "Maisons isolées en bord de route": "bord_de_route",
}


def generer_grille(scenario: str = "lisiere", nx: int = 60, ny: int = 40, graine: int = 42):
    """Renvoie (k, n) : classe de combustible et nombre de maisons par cellule."""
    rng = np.random.default_rng(graine)
    k = np.full((ny, nx), INCOMBUSTIBLE, dtype=int)
    n = np.zeros((ny, nx), dtype=int)

    if scenario == "lisiere":
        # massif à l'ouest, bande de lande en lisière, hameau posé dans la lande
        k[:, : int(nx * 0.65)] = FORET
        k[:, int(nx * 0.65) : int(nx * 0.85)] = LANDE
        x0, x1 = int(nx * 0.70), int(nx * 0.80)
        y0, y1 = int(ny * 0.40), int(ny * 0.60)
        n[y0:y1, x0:x1] = rng.integers(1, 4, size=(y1 - y0, x1 - x0))
        for _ in range(6):
            n[rng.integers(0, ny), rng.integers(int(nx * 0.85), nx)] = 1

    elif scenario == "hameau_foret":
        # forêt partout, clairière au centre avec un hameau compact
        k[:, :] = FORET
        x0, x1 = int(nx * 0.45), int(nx * 0.58)
        y0, y1 = int(ny * 0.40), int(ny * 0.62)
        k[y0:y1, x0:x1] = INCOMBUSTIBLE
        n[y0:y1, x0:x1] = rng.integers(1, 4, size=(y1 - y0, x1 - x0))

    elif scenario == "bord_de_route":
        # massif à l'ouest, route nord-sud, maisons égrenées côté est de la route
        k[:, : int(nx * 0.55)] = FORET
        k[:, int(nx * 0.55) : int(nx * 0.62)] = LANDE
        x_route = int(nx * 0.64)
        k[:, x_route : x_route + 1] = INCOMBUSTIBLE  # la route
        k[:, x_route + 1 :] = LANDE
        for y in range(2, ny - 2, 4):
            n[y, x_route + 2] = rng.integers(1, 3)

    else:
        raise ValueError(f"Scénario inconnu : {scenario}")

    # petit bruit de végétation, sauf sur les cellules bâties
    bruit = rng.random((ny, nx))
    melange = (k == FORET) & (bruit < 0.05) & (n == 0)
    k[melange] = LANDE

    return k, n


# ---------------------------------------------------------------------------
# Automate cellulaire + Monte-Carlo
# ---------------------------------------------------------------------------


def simuler_feu(k: np.ndarray, c0: tuple[int, int], conditions: Conditions, rng) -> np.ndarray:
    """Une réalisation : propage un feu depuis c0 jusqu'à extinction."""
    ny, nx = k.shape
    etat = np.full((ny, nx), ETAT_INTACTE, dtype=int)
    etat[c0] = ETAT_FEU
    front = [c0]

    while front:
        nouveau_front = []
        for (y, x) in front:
            for dy, dx in VOISINS:
                y2, x2 = y + dy, x + dx
                if 0 <= y2 < ny and 0 <= x2 < nx and etat[y2, x2] == ETAT_INTACTE:
                    p = facteurs_propagation(k[y2, x2], dy, dx, conditions, (y, x))
                    if rng.random() < p:
                        etat[y2, x2] = ETAT_FEU
                        nouveau_front.append((y2, x2))
            etat[y, x] = ETAT_BRULE
        front = nouveau_front

    return etat


def calculer_alea(k: np.ndarray, conditions: Conditions, n_simulations: int = 400, graine: int = 0):
    """Aléa par Monte-Carlo. La graine est fixée pour que deux scénarios comparés
    partagent la même suite de points d'éclosion : l'écart observé vient alors du
    modèle, pas du bruit d'échantillonnage."""
    rng = np.random.default_rng(graine)
    ny, nx = k.shape
    compteur = np.zeros((ny, nx), dtype=int)
    surfaces = np.zeros(n_simulations)

    vegetation = np.argwhere(k > INCOMBUSTIBLE)
    if len(vegetation) == 0:
        raise ValueError("Aucune cellule combustible : impossible de tirer une éclosion.")

    for m in range(n_simulations):
        c0 = tuple(vegetation[rng.integers(0, len(vegetation))])
        brulees = simuler_feu(k, c0, conditions, rng) == ETAT_BRULE
        compteur += brulees
        surfaces[m] = brulees.sum() * (DELTA**2) / 10_000  # en hectares

    p_brulage = compteur / n_simulations
    return LAMBDA_FEU_AN * p_brulage, p_brulage, surfaces


def calculer_risque(alea: np.ndarray, n: np.ndarray):
    enjeu = n * V_MAISON
    return enjeu, alea * enjeu * VULNERABILITE


def simuler_complet(k, n, conditions: Conditions, n_simulations: int = 400, graine: int = 0):
    """Enchaîne aléa -> enjeu -> risque et renvoie un dictionnaire de résultats."""
    alea, p_brulage, surfaces = calculer_alea(k, conditions, n_simulations, graine)
    enjeu, risque = calculer_risque(alea, n)
    return {
        "alea": alea,
        "p_brulage": p_brulage,
        "enjeu": enjeu,
        "risque": risque,
        "surfaces_ha": surfaces,
        "r_tot": float(risque.sum()),
        "alea_moyen": float(p_brulage[k > INCOMBUSTIBLE].mean()),
        "surface_moyenne_ha": float(surfaces.mean()),
    }


# ---------------------------------------------------------------------------
# Diagnostic de régime (percolation / saturation)
# ---------------------------------------------------------------------------


def diagnostic_regime(vent: Vent) -> dict:
    """Où se situe le modèle par rapport au seuil de percolation et au plafond p=1 ?

    C'est le garde-fou du modèle : sous 0.5 le feu s'éteint tout seul, au-dessus
    de 1 la propagation sous le vent devient certaine et le modèle cesse d'être
    stochastique dans cette direction.
    """
    f_max = max(facteur_vent(dy, dx, vent) for dy, dx in VOISINS)
    p_foret_brut = P_K[FORET] * f_max
    p_lande_brut = P_K[LANDE] * f_max

    if p_foret_brut >= 1.0:
        regime = "saturé"
        message = "Propagation certaine sous le vent : le modèle n'est plus stochastique dans cette direction."
    elif p_foret_brut > P_CRITIQUE:
        regime = "sur-critique"
        message = "Au-dessus du seuil de percolation : le feu peut traverser tout le massif."
    else:
        regime = "sous-critique"
        message = "Sous le seuil de percolation : le feu s'éteint spontanément après quelques cellules."

    return {
        "regime": regime,
        "message": message,
        "p_foret_brut": p_foret_brut,
        "p_lande_brut": p_lande_brut,
        "f_max": f_max,
    }


def vitesse_de_saturation(direction_deg: float) -> float:
    """Vitesse de vent à partir de laquelle la forêt sature (p >= 1) sous le vent."""
    thetas = [bearing(dy, dx) - direction_deg for dy, dx in VOISINS]
    f_ref = max(float(f_vent_calibree(t)) for t in thetas)
    if f_ref <= 1.0:
        return float("inf")
    # P_K[FORET] * f_ref ** (V / V_REF) = 1
    return VITESSE_REFERENCE * np.log(1.0 / P_K[FORET]) / np.log(f_ref)
