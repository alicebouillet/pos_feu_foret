"""
Pipeline vulnérabilité du bâti — test Deux-Sèvres
  0. Emprises des bâtiments résidentiels (BD TOPO)
  1. Couronnes 0–3 m / 0–5 m / 0–50 m autour de chaque bâtiment
  2. NDVI + masque de végétation (ORTHO IRC, flux WMS Géoplateforme)
  3. % de végétation par couronne
  4. Vignettes RVB 224x224 pour l'annotation des toitures

pip install geopandas pyogrio rasterio rasterstats requests pillow numpy shapely
"""
import io
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests
import shapely
from PIL import Image
from rasterio.merge import merge
from rasterio.transform import from_bounds
from rasterstats import zonal_stats
from shapely.geometry import box

# ------------------------------------------------------------------ PARAMÈTRES
BDTOPO_GPKG = Path("BDTOPO_3-5_TOUSTHEMES_GPKG_LAMB93_D079.gpkg")  # à adapter
COMMUNE = "Secondigny"                     # à adapter
DOSSIER = Path(f"sortie_{COMMUNE.lower().replace(' ', '_')}")

SURFACE_MIN = 20          # m², écarte abris et annexes
SEUIL_NDVI = 0.3          # à caler visuellement dans QGIS
RES_IRC = 0.5             # m/pixel pour le NDVI (suffisant pour la Zone Zéro)
TAILLE_DALLE = 1000       # m -> 2000 px à 0,5 m
COURONNES = (3, 5, 50)    # m

N_VIGNETTES = 100         # premier échantillon pour tester la variété des toits
MARGE_VIGNETTE = 2        # m autour de l'emprise
TAILLE_VIGNETTE = 224     # px

WMS_URL = "https://data.geopf.fr/wms-r/wms"
COUCHE_RVB = "HR.ORTHOIMAGERY.ORTHOPHOTOS"
COUCHE_IRC = "ORTHOIMAGERY.ORTHOPHOTOS.IRC"
CRS = "EPSG:2154"
PAUSE = 0.2               # s entre deux requêtes


# ------------------------------------------------------------------ WMS
def wms_getmap(couche, bounds, largeur, hauteur, essais=3):
    """Renvoie l'image (H, W, 3) uint8 d'une emprise Lambert 93."""
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
        "LAYERS": couche, "STYLES": "", "CRS": CRS,
        "BBOX": ",".join(f"{v:.2f}" for v in bounds),
        "WIDTH": largeur, "HEIGHT": hauteur, "FORMAT": "image/png",
    }
    for i in range(essais):
        r = requests.get(WMS_URL, params=params, timeout=90)
        if r.ok and r.headers.get("Content-Type", "").startswith("image"):
            return np.array(Image.open(io.BytesIO(r.content)).convert("RGB"))
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"WMS en échec ({couche}) : {r.status_code} {r.text[:300]}")


# ------------------------------------------------------------------ 0. EMPRISES
def charger_batiments():
    communes = gpd.read_file(BDTOPO_GPKG, layer="commune").to_crs(CRS)
    col = "nom_officiel" if "nom_officiel" in communes.columns else \
        next(c for c in communes.columns if "nom" in c.lower())
    sel = communes[communes[col].str.lower() == COMMUNE.lower()]
    if sel.empty:
        proches = communes[communes[col].str.lower().str.contains(COMMUNE.lower()[:5])][col]
        raise ValueError(f"Commune « {COMMUNE} » introuvable. Noms proches : {proches.tolist()}")
    contour = shapely.union_all(sel.geometry.values)

    bat = gpd.read_file(BDTOPO_GPKG, layer="batiment", mask=sel).to_crs(CRS)
    bat["geometry"] = shapely.force_2d(bat.geometry.values)
    bat = bat[bat.representative_point().within(contour)]
    if "usage_1" in bat.columns:
        bat = bat[bat["usage_1"] == "Résidentiel"]
    bat = bat[bat.area >= SURFACE_MIN].copy()
    bat["id_bat"] = bat["cleabs"] if "cleabs" in bat.columns else bat.index.astype(str)
    bat["surface_m2"] = bat.area.round(1)
    print(f"[0] {len(bat)} bâtiments résidentiels à {COMMUNE}")
    return bat.reset_index(drop=True)


# ------------------------------------------------------------------ 1. COURONNES
def creer_couronnes(bat):
    couronnes = {}
    for d in COURONNES:
        geom = bat.geometry.buffer(d).difference(bat.geometry)
        couronnes[d] = gpd.GeoDataFrame({"id_bat": bat["id_bat"].values},
                                        geometry=geom.values, crs=CRS)
        couronnes[d].to_file(DOSSIER / "couronnes.gpkg", layer=f"couronne_0_{d}m")
    print(f"[1] couronnes {COURONNES} m créées")
    return couronnes


# ------------------------------------------------------------------ 2. NDVI
def masque_vegetation(bat):
    dossier = DOSSIER / "dalles_irc"
    dossier.mkdir(parents=True, exist_ok=True)
    zone = shapely.union_all(bat.geometry.buffer(max(COURONNES) + 10).values)
    xmin, ymin, xmax, ymax = zone.bounds
    x0 = np.floor(xmin / TAILLE_DALLE) * TAILLE_DALLE
    y0 = np.floor(ymin / TAILLE_DALLE) * TAILLE_DALLE
    px = int(TAILLE_DALLE / RES_IRC)

    chemins = []
    for x in np.arange(x0, xmax, TAILLE_DALLE):
        for y in np.arange(y0, ymax, TAILLE_DALLE):
            b = (x, y, x + TAILLE_DALLE, y + TAILLE_DALLE)
            if not box(*b).intersects(zone):
                continue
            f_veg = dossier / f"veg_{int(x)}_{int(y)}.tif"
            f_ndvi = dossier / f"ndvi_{int(x)}_{int(y)}.tif"
            if not f_veg.exists():
                img = wms_getmap(COUCHE_IRC, b, px, px).astype("float32")
                pir, rouge = img[..., 0], img[..., 1]          # IRC : canal 1 = PIR, canal 2 = rouge
                ndvi = (pir - rouge) / np.maximum(pir + rouge, 1)
                veg = (ndvi > SEUIL_NDVI).astype("uint8")
                veg[img.min(axis=2) >= 250] = 255              # blanc = hors couverture
                profil = dict(driver="GTiff", width=px, height=px, count=1, crs=CRS,
                              transform=from_bounds(*b, px, px), compress="deflate")
                with rasterio.open(f_veg, "w", dtype="uint8", nodata=255, **profil) as dst:
                    dst.write(veg, 1)
                with rasterio.open(f_ndvi, "w", dtype="int16", nodata=-32768, **profil) as dst:
                    dst.write((ndvi * 1000).astype("int16"), 1)
                time.sleep(PAUSE)
            chemins.append(f_veg)

    arr, transform = merge([str(c) for c in chemins], nodata=255)
    sortie = DOSSIER / "masque_vegetation.tif"
    with rasterio.open(sortie, "w", driver="GTiff", width=arr.shape[2], height=arr.shape[1],
                       count=1, dtype="uint8", nodata=255, crs=CRS, transform=transform,
                       compress="deflate") as dst:
        dst.write(arr[0], 1)
    print(f"[2] {len(chemins)} dalles IRC -> {sortie}")
    return sortie


# ------------------------------------------------------------------ 3. STATS
def indicateurs_vegetation(bat, couronnes, masque):
    for d, gdf in couronnes.items():
        stats = zonal_stats(gdf, str(masque), stats=["mean"], nodata=255)
        bat[f"veg_0_{d}m"] = [round(s["mean"], 3) if s["mean"] is not None else np.nan
                              for s in stats]
    print("[3] indicateurs de végétation calculés")
    return bat


# ------------------------------------------------------------------ 4. VIGNETTES
def vignettes_toiture(bat):
    dossier = DOSSIER / "vignettes"
    dossier.mkdir(parents=True, exist_ok=True)
    ech = bat.sample(min(N_VIGNETTES, len(bat)), random_state=0)
    for _, r in ech.iterrows():
        f = dossier / f"{r.id_bat}.png"
        if f.exists():
            continue
        xmin, ymin, xmax, ymax = r.geometry.bounds
        cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
        demi = max(xmax - xmin, ymax - ymin) / 2 + MARGE_VIGNETTE   # carré : pas de déformation
        b = (cx - demi, cy - demi, cx + demi, cy + demi)
        Image.fromarray(wms_getmap(COUCHE_RVB, b, TAILLE_VIGNETTE, TAILLE_VIGNETTE)).save(f)
        time.sleep(PAUSE)
    print(f"[4] {len(ech)} vignettes -> {dossier}")


# ------------------------------------------------------------------ MAIN
if __name__ == "__main__":
    DOSSIER.mkdir(parents=True, exist_ok=True)
    bat = charger_batiments()
    couronnes = creer_couronnes(bat)
    masque = masque_vegetation(bat)
    bat = indicateurs_vegetation(bat, couronnes, masque)
    vignettes_toiture(bat)

    bat.to_file(DOSSIER / "batiments_indicateurs.gpkg", layer="batiments")
    bat.drop(columns="geometry").to_csv(DOSSIER / "batiments_indicateurs.csv", index=False)
    print(bat[[f"veg_0_{d}m" for d in COURONNES]].describe().round(3))