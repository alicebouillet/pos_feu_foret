"""
POS Feux de forêt — interface Streamlit de comparaison de scénarios.

Lancement :  streamlit run interface_risque_avec_relief.py

Le moteur lui-même est dans moteur_simulation_feu.py : cette page ne fait que l'appeler
et afficher les résultats.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from matplotlib.colors import BoundaryNorm, ListedColormap

import moteur_simulation_feu as mf

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
def charger_relief(forme, nx, ny, pente_deg, direction_montee):
    return mf.generer_relief(forme, nx, ny, pente_deg, direction_montee)


@st.cache_data(show_spinner=False)
def lancer_simulation(
    scenario, nx, ny, graine_grille, direction, vitesse, n_sim, graine_mc,
    forme_relief, pente_deg, direction_montee,
):
    k, n = charger_grille(scenario, nx, ny, graine_grille)
    z = charger_relief(forme_relief, nx, ny, pente_deg, direction_montee)
    conditions = mf.Conditions(
        vent=mf.Vent(direction_deg=direction, vitesse_kmh=vitesse), altitudes=z
    )
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

st.sidebar.header("Relief")
libelle_relief = st.sidebar.selectbox("Forme du terrain", list(mf.RELIEFS.keys()))
forme_relief = mf.RELIEFS[libelle_relief]

if forme_relief == "plat":
    pente_deg, direction_montee = 0.0, 90.0
else:
    pente_deg = st.sidebar.slider("Pente maximale (°)", 0, 25, 5, step=1)
    direction_montee = (
        st.sidebar.slider("Cap vers lequel le terrain monte", 0, 359, 90, step=5)
        if forme_relief == "versant"
        else 90.0
    )

z = charger_relief(forme_relief, nx, ny, pente_deg, direction_montee)
info_relief = mf.resume_relief(z)
if z is not None:
    st.sidebar.caption(
        f"Dénivelé {info_relief['denivele_m']:.0f} m — pente max {info_relief['pente_max_deg']:.1f}° "
        f"→ le feu se propage {info_relief['facteur_max']:.1f}× plus facilement en montée."
    )

st.sidebar.header("Monte-Carlo")
n_sim = st.sidebar.select_slider("Nombre de simulations", [50, 100, 200, 400, 800, 1600], value=400)
st.sidebar.caption(
    "N = 400 est la valeur du doc de départ, et c'est aussi le minimum pour qu'un écart "
    "entre deux scénarios de vent ressorte du bruit. En dessous, les comparaisons ne sont "
    "pas interprétables."
)
graine_mc = st.sidebar.number_input("Graine aléatoire", value=0, step=1)
st.sidebar.caption(
    f"Chaque simulation tire **son propre** point de départ au hasard dans la végétation : "
    f"{n_sim} simulations = {n_sim} départs dispersés sur tout le massif. "
    "Ce qui est partagé entre A et B, c'est la *liste* de ces départs — la simulation n°7 de A "
    "part du même endroit que la n°7 de B — pour que l'écart mesuré vienne du vent et non du "
    "hasard du tirage."
)

k, n = charger_grille(scenario, nx, ny, 42)

# ---------------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------------

st.title("Risque feux de forêt — effet du vent et du relief")
st.caption(
    "R = Aléa × Enjeu × Vulnérabilité. L'aléa est estimé par Monte-Carlo sur un automate "
    "cellulaire stochastique ; le vent et la pente déforment les probabilités de propagation "
    "(`p = p_combustible × f_vent × f_pente`)."
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
    args_relief = (forme_relief, pente_deg, direction_montee)
    res_a = lancer_simulation(scenario, nx, ny, 42, dir_a, vit_a, n_sim, graine_mc, *args_relief)
    res_b = lancer_simulation(scenario, nx, ny, 42, dir_b, vit_b, n_sim, graine_mc, *args_relief)

vent_a = mf.Vent(dir_a, vit_a)
vent_b = mf.Vent(dir_b, vit_b)

# ---------------------------------------------------------------------------
# Chiffres clés
# ---------------------------------------------------------------------------

st.divider()


def fr(x: float, signe: bool = False) -> str:
    return f"{x:{'+' if signe else ''},.0f}".replace(",", " ")


# Les deux scénarios partagent leurs points d'éclosion : les pertes sont appariées
# simulation par simulation, donc l'incertitude sur l'ÉCART se calcule sur les paires
# (et elle est plus petite que si les deux scénarios étaient tirés indépendamment).
ecart = res_b["r_tot"] - res_a["r_tot"]
diff_maisons = res_b["maisons_brulees"] - res_a["maisons_brulees"]
echelle = mf.LAMBDA_FEU_AN * mf.V_MAISON * mf.VULNERABILITE
se_ecart = echelle * diff_maisons.std(ddof=1) / np.sqrt(len(diff_maisons))

m1, m2, m3, m4 = st.columns(4)
m1.metric("Risque total A", f"{fr(res_a['r_tot'])} €/an", help=f"± {fr(res_a['r_tot_erreur_type'])} €/an (erreur-type Monte-Carlo)")
m2.metric(
    "Risque total B",
    f"{fr(res_b['r_tot'])} €/an",
    delta=f"{fr(ecart, signe=True)} €/an",
    help=f"± {fr(res_b['r_tot_erreur_type'])} €/an (erreur-type Monte-Carlo)",
)
m3.metric("Aléa moyen A → B", f"{res_a['alea_moyen']:.3f} → {res_b['alea_moyen']:.3f}")
m4.metric(
    "Surface brûlée moyenne A → B",
    f"{res_a['surface_moyenne_ha']:.0f} → {res_b['surface_moyenne_ha']:.0f} ha",
)

st.caption(
    f"Incertitude Monte-Carlo : A = {fr(res_a['r_tot'])} ± {fr(res_a['r_tot_erreur_type'])} €/an, "
    f"B = {fr(res_b['r_tot'])} ± {fr(res_b['r_tot_erreur_type'])} €/an. "
    f"Écart B − A = {fr(ecart, signe=True)} ± {fr(se_ecart)} €/an (erreur-type appariée)."
)

if abs(ecart) < 2 * se_ecart:
    st.warning(
        f"**Écart non significatif.** L'écart entre A et B ({fr(ecart, signe=True)} €/an) est plus petit "
        f"que 2 erreurs-types ({fr(2 * se_ecart)} €/an) : il est indiscernable du bruit d'échantillonnage. "
        "Augmente le nombre de simulations, ou choisis un territoire comptant plus de maisons.",
        icon="⚠️",
    )

# ---------------------------------------------------------------------------
# Avertissement de régime (percolation / saturation)
# ---------------------------------------------------------------------------

for nom, vent in [("A", vent_a), ("B", vent_b)]:
    diag = mf.diagnostic_regime(vent, z)
    detail = f"vent ×{diag['f_vent_max']:.2f}"
    if z is not None:
        detail += f", pente ×{diag['f_pente_max']:.2f}"
    texte = (
        f"**Scénario {nom} — régime {diag['regime']}** "
        f"(p forêt dans la direction la plus favorable = {min(diag['p_foret_brut'], 1):.2f} "
        f"[{detail}], seuil de percolation = {mf.P_CRITIQUE}). "
        f"{diag['message']}"
    )
    if diag["regime"] == "saturé":
        st.error(texte, icon="⚠️")
    elif diag["regime"] == "sous-critique":
        st.info(texte, icon="ℹ️")
    else:
        st.success(texte, icon="✅")

v_sat_a, v_sat_b = mf.vitesse_de_saturation(dir_a, z), mf.vitesse_de_saturation(dir_b, z)
if v_sat_a == 0 or v_sat_b == 0:
    st.caption(
        "⚠️ La pente seule suffit à saturer la propagation : au-delà de 10,2° de pente montante, "
        f"p = {mf.P_K[mf.FORET]} × exp(0,078 × θ) dépasse déjà 1 à vent nul. Le curseur de vent "
        "n'a plus aucun effet en montée, quelle que soit sa valeur."
    )
else:
    st.caption(
        f"Vitesse de saturation : {v_sat_a:.0f} km/h pour la direction de A, "
        f"{v_sat_b:.0f} km/h pour celle de B. Au-delà, augmenter le vent n'a plus aucun effet. "
        + ("La pente en consomme déjà une partie." if z is not None else "")
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
    titre = "Territoire"
    if z is not None:
        # courbes de niveau par-dessus le combustible
        niveaux = ax.contour(z, levels=7, colors="#2b2b2b", linewidths=0.7, alpha=0.75)
        ax.clabel(niveaux, inline=True, fontsize=6, fmt="%.0f m")
        titre += f" + relief ({info_relief['denivele_m']:.0f} m de dénivelé)"
    ax.set_title(titre, fontsize=10)
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


def paire_de_cartes(champ: str, titre: str, unite: str = ""):
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
    fig.colorbar(im, ax=list(axes[1:]), fraction=0.03, pad=0.02, label=f"{titre} {unite}".strip())

    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])
    return fig


with onglet_alea:
    st.pyplot(paire_de_cartes("alea", "Aléa A(c)"), use_container_width=True)
    st.caption(
        f"A(c) = λ · P̂(brûlage), avec λ = {mf.LAMBDA_FEU_AN} départ de feu par an sur le domaine : "
        "à lire comme la part d'années où la cellule brûle. "
        "Échelle de couleur commune aux deux scénarios, donc directement comparables."
    )
    st.info(
        f"**Ces cartes ne sont pas des feux.** Chacune superpose {n_sim} feux partis de "
        f"{n_sim} endroits différents, tirés au hasard dans la végétation. Un feu isolé, lui, "
        "est une tache compacte — déplie ci-dessous pour en voir.",
        icon="💡",
    )

    with st.expander("Voir des feux individuels (et leurs points de départ)"):
        scenario_vu = st.radio(
            "Scénario", ["A", "B"], horizontal=True, key="choix_scenario_individuel"
        )
        vent_vu = vent_a if scenario_vu == "A" else vent_b

        vegetation = np.argwhere(k > mf.INCOMBUSTIBLE)
        indices = np.random.default_rng(graine_mc).integers(0, len(vegetation), size=n_sim)
        conditions_vu = mf.Conditions(vent=vent_vu, altitudes=z)

        fig, axes = plt.subplots(1, 4, figsize=(16, 3.6))
        for ax, m in zip(axes, range(4)):
            etat = mf.simuler_feu(
                k, tuple(vegetation[indices[m]]), conditions_vu,
                np.random.default_rng([graine_mc, m]),
            )
            brulees = etat == mf.ETAT_BRULE
            ax.imshow(k, cmap=CMAP_COMBUSTIBLE, norm=NORM_COMBUSTIBLE, origin="upper", alpha=0.35)
            ax.imshow(
                np.ma.masked_where(~brulees, brulees.astype(float)),
                cmap=ListedColormap(["#b5341f"]), origin="upper", vmin=0, vmax=1,
            )
            y0, x0 = vegetation[indices[m]]
            ax.plot(x0, y0, marker="*", ms=15, color="#111", mec="white", mew=1.2)
            ax.set_title(
                f"Simulation n°{m + 1} — {brulees.sum() * mf.DELTA**2 / 10_000:.0f} ha",
                fontsize=10,
            )
            ax.set_xticks([]); ax.set_yticks([])
        st.pyplot(fig, use_container_width=True)
        st.caption(
            "L'étoile marque le point de départ : il change à chaque simulation. "
            f"La carte d'aléa ci-dessus est la moyenne de {n_sim} feux comme ceux-là."
        )

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
| H5 | Pas de pente | **levée** — `f_pente = exp(0,078·θ)`, θ en degrés, d'après Alexandridis et al. (2008) ; double tous les 10° de montée |
| H6 | Éclosion uniforme dans la végétation | encore active |
| H7 | Pas de sautes de feu (brandons) | encore active |
| H8 | V constante (0,6) | encore active |
| H9 | Pas d'intervention des secours | encore active |

L'humidité n'apparaît pas dans la liste d'origine : elle reste à brancher dans
`facteur_humidite()`.

**Attention** : la pente consomme très vite la marge avant saturation. Au-delà de
**10,2°** de pente montante, `p = 0,45 × exp(0,078·θ)` dépasse 1 à vent nul : la
propagation en montée devient certaine et le modèle n'est plus stochastique dans
cette direction. Le temps de résidence τ (H2) est donc à traiter en priorité, avant
d'exploiter sérieusement le relief.
        """
    )