"""
POS Feux de forêt — interface Streamlit de comparaison de scénarios.

Lancement :  streamlit run app_feu.py

Le modèle lui-même est dans moteur_feu.py : cette page ne fait que l'appeler
et afficher les résultats.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from matplotlib.colors import BoundaryNorm, ListedColormap

import moteur_feu as mf

st.set_page_config(page_title="POS — risque feux de forêt", layout="wide")

CMAP_COMBUSTIBLE = ListedColormap(["#d9d9d9", "#c7e08e", "#2f6b3a"])
NORM_COMBUSTIBLE = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], 3)
CMAP_ALEA = "YlOrRd"
COULEUR_A, COULEUR_B = "#1f6fb4", "#c0392b"

ROSE = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]


def nom_direction(deg: float) -> str:
    return ROSE[int((deg % 360) / 22.5 + 0.5) % 16]


# ---------------------------------------------------------------------------
# Calculs (mis en cache : bouger un curseur ne recalcule que le scénario touché)
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def charger_grille(scenario: str, nx: int, ny: int, graine: int):
    return mf.generer_grille(scenario, nx, ny, graine)


@st.cache_data(show_spinner=False)
def lancer_simulation(scenario, nx, ny, graine_grille, direction, vitesse, n_sim, graine_mc):
    k, n = charger_grille(scenario, nx, ny, graine_grille)
    conditions = mf.Conditions(vent=mf.Vent(direction_deg=direction, vitesse_kmh=vitesse))
    return mf.simuler_complet(k, n, conditions, n_sim, graine_mc)


# ---------------------------------------------------------------------------
# Barre latérale : territoire et paramètres de simulation
# ---------------------------------------------------------------------------

st.sidebar.header("Territoire")
libelle_scenario = st.sidebar.selectbox("Scénario d'implantation", list(mf.SCENARIOS.keys()))
scenario = mf.SCENARIOS[libelle_scenario]

nx = st.sidebar.slider("Largeur (cellules)", 30, 100, 60, step=10)
ny = st.sidebar.slider("Hauteur (cellules)", 20, 80, 40, step=10)
st.sidebar.caption(f"Cellules de {mf.DELTA} m → domaine de {nx * mf.DELTA / 1000:.1f} × {ny * mf.DELTA / 1000:.1f} km")

st.sidebar.header("Monte-Carlo")
n_sim = st.sidebar.select_slider("Nombre de simulations", [50, 100, 200, 400, 800], value=200)
st.sidebar.caption("Le doc de départ utilise N = 400. Moins = plus rapide mais plus bruité.")
graine_mc = st.sidebar.number_input("Graine aléatoire", value=0, step=1)
st.sidebar.caption(
    "Les deux scénarios partagent la même graine : l'écart observé vient du vent, "
    "pas du bruit d'échantillonnage."
)

k, n = charger_grille(scenario, nx, ny, 42)

# ---------------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------------

st.title("Risque feux de forêt — effet du vent")
st.caption(
    "R = Aléa × Enjeu × Vulnérabilité. L'aléa est estimé par Monte-Carlo sur un automate "
    "cellulaire stochastique ; le vent déforme les probabilités de propagation."
)

# ---------------------------------------------------------------------------
# Réglage des deux scénarios de vent
# ---------------------------------------------------------------------------

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Scénario A")
    dir_a = st.slider("Direction du vent (cap vers lequel il souffle)", 0, 359, 90, step=5, key="dir_a")
    vit_a = st.slider("Vitesse du vent (km/h)", 0, 50, 20, step=1, key="vit_a")
    st.caption(f"Vent soufflant vers le **{nom_direction(dir_a)}** à {vit_a} km/h")

with col_b:
    st.subheader("Scénario B")
    dir_b = st.slider("Direction du vent (cap vers lequel il souffle)", 0, 359, 45, step=5, key="dir_b")
    vit_b = st.slider("Vitesse du vent (km/h)", 0, 50, 25, step=1, key="vit_b")
    st.caption(f"Vent soufflant vers le **{nom_direction(dir_b)}** à {vit_b} km/h")

with st.spinner("Simulation en cours…"):
    res_a = lancer_simulation(scenario, nx, ny, 42, dir_a, vit_a, n_sim, graine_mc)
    res_b = lancer_simulation(scenario, nx, ny, 42, dir_b, vit_b, n_sim, graine_mc)

vent_a = mf.Vent(dir_a, vit_a)
vent_b = mf.Vent(dir_b, vit_b)

# ---------------------------------------------------------------------------
# Chiffres clés
# ---------------------------------------------------------------------------

st.divider()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Risque total A", f"{res_a['r_tot']:,.0f} €/an".replace(",", " "))
m2.metric(
    "Risque total B",
    f"{res_b['r_tot']:,.0f} €/an".replace(",", " "),
    delta=f"{res_b['r_tot'] - res_a['r_tot']:+,.0f} €/an".replace(",", " "),
)
m3.metric("Aléa moyen A → B", f"{res_a['alea_moyen']:.3f} → {res_b['alea_moyen']:.3f}")
m4.metric(
    "Surface brûlée moyenne A → B",
    f"{res_a['surface_moyenne_ha']:.0f} → {res_b['surface_moyenne_ha']:.0f} ha",
)

# ---------------------------------------------------------------------------
# Avertissement de régime (percolation / saturation)
# ---------------------------------------------------------------------------

for nom, vent in [("A", vent_a), ("B", vent_b)]:
    diag = mf.diagnostic_regime(vent)
    texte = (
        f"**Scénario {nom} — régime {diag['regime']}** "
        f"(p forêt sous le vent = {diag['p_foret_brut']:.2f}, seuil de percolation = {mf.P_CRITIQUE}). "
        f"{diag['message']}"
    )
    if diag["regime"] == "saturé":
        st.error(texte, icon="⚠️")
    elif diag["regime"] == "sous-critique":
        st.info(texte, icon="ℹ️")
    else:
        st.success(texte, icon="✅")

v_sat_a, v_sat_b = mf.vitesse_de_saturation(dir_a), mf.vitesse_de_saturation(dir_b)
st.caption(
    f"Vitesse de saturation : {v_sat_a:.0f} km/h pour la direction de A, "
    f"{v_sat_b:.0f} km/h pour celle de B. Au-delà, augmenter le vent n'a plus aucun effet."
)

# ---------------------------------------------------------------------------
# Cartes
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Cartes")

onglet_alea, onglet_risque = st.tabs(["Aléa A(c)", "Risque R(c)"])


def carte_territoire(ax):
    ax.imshow(k, cmap=CMAP_COMBUSTIBLE, norm=NORM_COMBUSTIBLE, origin="upper")
    ys, xs = np.nonzero(n)
    ax.scatter(xs, ys, s=12, c="#c0392b", marker="s", label="maison(s)")
    ax.set_title("Territoire", fontsize=10)
    ax.legend(loc="lower right", fontsize=7)


def fleche_vent(ax, vent: mf.Vent):
    """Flèche indiquant vers où souffle le vent (rien si vent nul)."""
    if vent.vitesse_kmh == 0:
        return
    angle = np.radians(vent.direction_deg)
    dx, dy = np.sin(angle), -np.cos(angle)
    ax.annotate(
        "",
        xy=(0.88 + 0.08 * dx, 0.88 + 0.08 * dy),
        xytext=(0.88 - 0.08 * dx, 0.88 - 0.08 * dy),
        xycoords="axes fraction",
        arrowprops=dict(arrowstyle="-|>", color="#222", lw=2),
    )


def paire_de_cartes(champ: str, titre: str, unite: str):
    vmax = max(res_a[champ].max(), res_b[champ].max())
    vmax = vmax if vmax > 0 else 1.0
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    carte_territoire(axes[0])
    for ax, res, vent, nom in [(axes[1], res_a, vent_a, "A"), (axes[2], res_b, vent_b, "B")]:
        im = ax.imshow(res[champ], cmap=CMAP_ALEA, origin="upper", vmin=0, vmax=vmax)
        ax.set_title(
            f"{nom} — vers le {nom_direction(vent.direction_deg)}, {vent.vitesse_kmh:.0f} km/h",
            fontsize=10,
        )
        fleche_vent(ax, vent)
    fig.colorbar(im, ax=list(axes[1:]), fraction=0.03, pad=0.02, label=f"{titre} {unite}")

    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])
    return fig


with onglet_alea:
    st.pyplot(paire_de_cartes("alea", "Aléa A(c)", "[fréq. annuelle]"), use_container_width=True)
    st.caption("Échelle de couleur commune aux deux scénarios : les cartes sont directement comparables.")

with onglet_risque:
    st.pyplot(paire_de_cartes("risque", "Risque R(c)", "[€/an]"), use_container_width=True)
    st.caption("Le risque ne s'allume que là où l'aléa rencontre des maisons (enjeu non nul).")

# ---------------------------------------------------------------------------
# Anisotropie du vent + dispersion des surfaces brûlées
# ---------------------------------------------------------------------------

st.divider()
col_rose, col_hist = st.columns(2)

with col_rose:
    st.subheader("Anisotropie induite par le vent")
    thetas = np.linspace(0, 360, 361)
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={"projection": "polar"})
    for vent, couleur, nom in [(vent_a, COULEUR_A, "A"), (vent_b, COULEUR_B, "B")]:
        f = mf.f_vent_calibree(thetas - vent.direction_deg) ** (vent.vitesse_kmh / mf.VITESSE_REFERENCE)
        ax.plot(np.radians(thetas), f, color=couleur, lw=2, label=f"Scénario {nom}")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_xticks(np.radians([0, 90, 180, 270]))
    ax.set_xticklabels(["N", "E", "S", "O"])
    ax.set_title("Facteur multiplicatif f_vent selon la direction", fontsize=10, pad=15)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=9)
    st.pyplot(fig, use_container_width=True)
    st.caption("À vitesse nulle, le tracé est un cercle de rayon 1 : aucune direction privilégiée.")

with col_hist:
    st.subheader("Dispersion des surfaces brûlées")
    fig, ax = plt.subplots(figsize=(6, 4.6))
    bornes = np.histogram_bin_edges(
        np.concatenate([res_a["surfaces_ha"], res_b["surfaces_ha"]]), bins=30
    )
    ax.hist(res_a["surfaces_ha"], bins=bornes, color=COULEUR_A, alpha=0.6, label="Scénario A")
    ax.hist(res_b["surfaces_ha"], bins=bornes, color=COULEUR_B, alpha=0.6, label="Scénario B")
    ax.set_xlabel("Surface brûlée par simulation (ha)")
    ax.set_ylabel("Nombre de simulations")
    ax.legend(fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    st.pyplot(fig, use_container_width=True)
    st.caption(
        "Rappel du doc : la carte d'aléa est une moyenne sur ces N réalisations — "
        "aucune simulation individuelle ne lui ressemble."
    )

# ---------------------------------------------------------------------------
# Hypothèses encore en vigueur
# ---------------------------------------------------------------------------

with st.expander("Hypothèses du modèle (et ce qu'il reste à lever)"):
    st.markdown(
        """
| # | Hypothèse | Statut |
|---|---|---|
| H1 | Propagation aux 4 voisines seulement | encore active — front en losange |
| H2 | Une seule tentative par interface | encore active — percolation, seuil à 0,5 |
| H3 | p ne dépend que de la cellule réceptrice | encore active |
| H4 | Vent fixe, uniforme, constant | **partiellement levée** — direction et vitesse réglables, mais toujours uniformes dans l'espace et constantes dans le temps |
| H5 | Pas de pente | encore active — `facteur_pente()` à implémenter |
| H6 | Éclosion uniforme dans la végétation | encore active |
| H7 | Pas de sautes de feu (brandons) | encore active |
| H8 | V constante (0,6) | encore active |
| H9 | Pas d'intervention des secours | encore active |

L'humidité n'apparaît pas dans la liste d'origine : elle rejoindra `facteur_humidite()`,
au même titre que la pente.
        """
    )
