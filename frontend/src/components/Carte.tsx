/**
 * Carte principale AgroSentry (MapLibre GL JS 3D).
 *
 * - trois couches raster NASA GIBS : NDVI 8 jours, température de surface, couleur vraie ;
 * - opacité réglable par couche, légendes avec unités et date du composite ;
 * - date bornée au début de l'archive GIBS (2025-02-12) et alignée sur les
 *   composites de 8 jours, avec repli automatique sur le composite précédent
 *   quand une tuile manque ;
 * - bascule 2D / 3D et trois fonds de carte (clair, plan, satellite) ;
 * - clic sur la carte → appel `/api/point/` et popup avec source, confiance et
 *   mention « à valider avec un agronome ».
 */

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { ApiError, getPoint, type ReponsePoint } from "../api";

const CENTRE: [number, number] = [11.23, 4.75];
const ZOOM_INITIAL = 10.5;
const DATE_MIN = "2025-02-12";
const PAS_COMPOSITE_JOURS = 8;
const REPLIS_MAX = 4;
const ATTRIBUTION_GIBS = "NASA GIBS / EOSDIS";
const ATTRIBUTION_FOND = "OpenFreeMap · OpenStreetMap";
const URL_RELIEF =
  "https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png";

type IdCouche = "ndvi" | "lst" | "truecolor";
type Fond = "clair" | "plan" | "satellite";

interface ConfigCouche {
  id: IdCouche;
  nom: string;
  jeuGibs: string;
  matrice: string;
  maxzoom: number;
  unite: string;
  description: string;
  legende: Array<{ couleur: string; libelle: string }>;
}

const COUCHES: ConfigCouche[] = [
  {
    id: "ndvi",
    nom: "Végétation (NDVI)",
    jeuGibs: "MODIS_Terra_NDVI_8Day",
    matrice: "GoogleMapsCompatible_Level9",
    maxzoom: 9,
    unite: "indice 0 – 1",
    description:
      "Vert = végétation active, brun = sol nu ou végétation sèche. Composite de 8 jours.",
    legende: [
      { couleur: "#8c6b3f", libelle: "0,2 — sol nu" },
      { couleur: "#d9d18a", libelle: "0,5 — végétation clairsemée" },
      { couleur: "#2e7d32", libelle: "0,8 — végétation dense" },
    ],
  },
  {
    id: "lst",
    nom: "Température de surface",
    jeuGibs: "MODIS_Terra_Land_Surface_Temp_Day",
    matrice: "GoogleMapsCompatible_Level7",
    maxzoom: 7,
    unite: "°C (jour)",
    description:
      "Température radiométrique du sol en journée. Utile pour repérer les parcelles qui chauffent.",
    legende: [
      { couleur: "#3b3b98", libelle: "≈ 15 °C" },
      { couleur: "#e0b43a", libelle: "≈ 30 °C" },
      { couleur: "#b3261e", libelle: "≈ 45 °C et plus" },
    ],
  },
  {
    id: "truecolor",
    nom: "Couleur vraie",
    jeuGibs: "MODIS_Terra_CorrectedReflectance_TrueColor",
    matrice: "GoogleMapsCompatible_Level9",
    maxzoom: 9,
    unite: "image (sans unité)",
    description:
      "Image satellite en couleurs naturelles : nuages, sols, cours d'eau visibles.",
    legende: [
      { couleur: "#f2f2f2", libelle: "nuages" },
      { couleur: "#4e7a3a", libelle: "végétation" },
      { couleur: "#8a6b4a", libelle: "sol nu" },
    ],
  },
];

const STYLES_FOND: Record<Fond, string | maplibregl.StyleSpecification> = {
  clair: "https://tiles.openfreemap.org/styles/positron",
  plan: "https://tiles.openfreemap.org/styles/bright",
  satellite: {
    version: 8,
    sources: {
      esri: {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        attribution: "Esri, Maxar, Earthstar Geographics",
      },
    },
    layers: [{ id: "esri", type: "raster", source: "esri" }],
  },
};

const FONDS: Array<{ id: Fond; libelle: string }> = [
  { id: "clair", libelle: "Fond clair" },
  { id: "plan", libelle: "Fond plan" },
  { id: "satellite", libelle: "Fond satellite" },
];

const TITRES_COUCHE: Record<IdCouche, string> = {
  ndvi: "NDVI",
  lst: "Température",
  truecolor: "Couleur vraie",
};

/* ------------------------------------------------------------------ dates */

function joursDepuis(iso: string): number {
  const [annee, mois, jour] = iso.split("-").map(Number);
  return Math.floor(Date.UTC(annee, mois - 1, jour) / 86_400_000);
}

function ajouterJours(iso: string, jours: number): string {
  const [annee, mois, jour] = iso.split("-").map(Number);
  return new Date(Date.UTC(annee, mois - 1, jour + jours))
    .toISOString()
    .slice(0, 10);
}

/** Aligne une date sur le composite de 8 jours précédent (jamais dans le futur). */
function alignerDate(iso: string): string {
  const minimum = joursDepuis(DATE_MIN);
  const cible = Math.max(minimum, joursDepuis(iso));
  const pas = Math.floor((cible - minimum) / PAS_COMPOSITE_JOURS);
  return ajouterJours(DATE_MIN, pas * PAS_COMPOSITE_JOURS);
}

function dateDuJour(): string {
  return new Date().toISOString().slice(0, 10);
}

function urlTuiles(couche: ConfigCouche, dateComposite: string, replis: number): string {
  const date = ajouterJours(dateComposite, -PAS_COMPOSITE_JOURS * replis);
  return (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/" +
    `${couche.jeuGibs}/default/${date}/${couche.matrice}/{z}/{y}/{x}.png`
  );
}

function dateAffichee(iso: string): string {
  const [annee, mois, jour] = iso.split("-");
  return `${jour}/${mois}/${annee}`;
}

/* ------------------------------------------------------------------ popup */

const CORRESPONDANCES_HTML: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

function echapper(valeur: unknown): string {
  return String(valeur ?? "—").replace(
    /[&<>"']/g,
    (caractere) => CORRESPONDANCES_HTML[caractere],
  );
}

function valeurOuInconnue(valeur: number | null | undefined, unite: string): string {
  return typeof valeur === "number" ? `${valeur} ${unite}` : "donnée absente";
}

function htmlPoint(donnees: ReponsePoint): string {
  const meteo = donnees.meteo;
  const risque = donnees.risque;
  const score =
    typeof risque.score === "number"
      ? `${Math.round(risque.score * 100)} %`
      : "non calculé";

  return `
    <div class="popup-agrosentry">
      <h3>${echapper(donnees.zone?.nom ?? "Zone inconnue")}</h3>
      <p class="popup-coords">
        ${echapper(donnees.position.latitude.toFixed(3))}° N ·
        ${echapper(donnees.position.longitude.toFixed(3))}° E ·
        à ${echapper(donnees.distance_km)} km du centre de la zone
      </p>
      <ul class="popup-liste">
        <li>Pluie 7 jours : ${echapper(valeurOuInconnue(meteo.pluie_7j_mm, "mm"))}</li>
        <li>Pluie 30 jours : ${echapper(valeurOuInconnue(meteo.pluie_30j_mm, "mm"))}</li>
        <li>Tmax moyenne 30 jours : ${echapper(
          valeurOuInconnue(meteo.temp_max_moyenne_30j_c, "°C"),
        )}</li>
        <li>Dernière donnée : ${echapper(meteo.derniere_date ?? "inconnue")}</li>
      </ul>
      <p class="popup-risque">
        <strong>Risque de poche de sécheresse :</strong>
        ${echapper(risque.niveau ?? "indisponible")} (${echapper(score)}),
        confiance ${echapper(risque.confiance)}
      </p>
      ${
        risque.explication
          ? `<p class="popup-explication">${echapper(risque.explication)}</p>`
          : ""
      }
      <p class="popup-source">
        Source : ${echapper(donnees.source)}<br />
        ${echapper(donnees.resolution)}
      </p>
      <p class="popup-demo">Démonstration — rotations issues de fixtures, pas d'une parcelle réelle.</p>
      <p class="popup-agronome">⚠ À valider avec un agronome.</p>
    </div>
  `;
}

function htmlErreur(erreur: unknown): string {
  const message =
    erreur instanceof ApiError ? erreur.message : "Erreur inattendue.";
  return `
    <div class="popup-agrosentry">
      <h3>Point non disponible</h3>
      <p>${echapper(message)}</p>
      <p class="popup-agronome">⚠ Valeurs non calculées : ne rien décider sur cette base.</p>
    </div>
  `;
}

/* --------------------------------------------------------------- composant */

export default function Carte() {
  const conteneurRef = useRef<HTMLDivElement | null>(null);
  const carteRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const requeteRef = useRef<AbortController | null>(null);
  const urlsInstallees = useRef<Partial<Record<IdCouche, string>>>({});
  const dernierRepli = useRef<Partial<Record<IdCouche, number>>>({});
  const replisRef = useRef<Record<IdCouche, number>>({
    ndvi: 0,
    lst: 0,
    truecolor: 0,
  });

  const [fond, setFond] = useState<Fond>("clair");
  const [mode3D, setMode3D] = useState(true);
  const [dateChoisie, setDateChoisie] = useState<string>(alignerDate(dateDuJour()));
  const [visibles, setVisibles] = useState<Record<IdCouche, boolean>>({
    ndvi: true,
    lst: false,
    truecolor: false,
  });
  const [opacites, setOpacites] = useState<Record<IdCouche, number>>({
    ndvi: 0.75,
    lst: 0.6,
    truecolor: 0.85,
  });
  const [replis, setReplis] = useState<Record<IdCouche, number>>({
    ndvi: 0,
    lst: 0,
    truecolor: 0,
  });
  const [messageRepli, setMessageRepli] = useState<string | null>(null);
  const [horsLigne, setHorsLigne] = useState(!navigator.onLine);
  const [erreurFond, setErreurFond] = useState<string | null>(null);
  const terrainRef = useRef<string | null>(null);
  const premierFond = useRef(true);

  const dateAligne = alignerDate(dateChoisie);
  replisRef.current = replis;

  const appliquerRef = useRef<() => void>(() => undefined);
  const gererErreurRef = useRef<(evenement: unknown) => void>(() => undefined);
  const gererClicRef = useRef<(evenement: maplibregl.MapMouseEvent) => void>(
    () => undefined,
  );

  /**
   * Réessaie jusqu'à ce que le style soit réellement chargé.
   * `setStyle` est asynchrone : installer des sources pendant la
   * reconstruction ferait perdre les couches (écran vide).
   */
  const appliquerDesQuePretRef = useRef<() => void>(() => undefined);
  appliquerDesQuePretRef.current = () => {
    let essais = 0;
    const tenter = () => {
      const carte = carteRef.current;
      if (!carte) return;
      if (carte.isStyleLoaded()) {
        appliquerRef.current();
        return;
      }
      essais += 1;
      if (essais > 120) return;
      window.setTimeout(tenter, 50);
    };
    tenter();
  };

  /* Applique fond, relief et couches raster à l'état courant. */
  appliquerRef.current = () => {
    const carte = carteRef.current;
    if (!carte || !carte.isStyleLoaded()) return;

    if (!carte.getSource("relief")) {
      carte.addSource("relief", {
        type: "raster-dem",
        tiles: [URL_RELIEF],
        encoding: "terrarium",
        tileSize: 256,
        maxzoom: 15,
      });
    }
    if (!carte.getLayer("relief-ombrage")) {
      carte.addLayer({
        id: "relief-ombrage",
        type: "hillshade",
        source: "relief",
        paint: { "hillshade-exaggeration": 0.3 },
      });
    }
    const terrainVoulu = mode3D ? "3d" : "2d";
    if (terrainRef.current !== terrainVoulu) {
      carte.setTerrain(mode3D ? { source: "relief", exaggeration: 1.4 } : null);
      terrainRef.current = terrainVoulu;
    }

    for (const couche of COUCHES) {
      const url = urlTuiles(couche, dateAligne, replis[couche.id]);
      if (urlsInstallees.current[couche.id] !== url) {
        if (carte.getLayer(couche.id)) carte.removeLayer(couche.id);
        if (carte.getSource(couche.id)) carte.removeSource(couche.id);
        urlsInstallees.current[couche.id] = url;
      }
      if (!carte.getSource(couche.id)) {
        carte.addSource(couche.id, {
          type: "raster",
          tiles: [url],
          tileSize: 256,
          maxzoom: couche.maxzoom,
          attribution: ATTRIBUTION_GIBS,
        });
      }
      if (!carte.getLayer(couche.id)) {
        carte.addLayer({
          id: couche.id,
          type: "raster",
          source: couche.id,
          layout: { visibility: visibles[couche.id] ? "visible" : "none" },
          paint: { "raster-opacity": opacites[couche.id] },
        });
      } else {
        const visibiliteVoulue = visibles[couche.id] ? "visible" : "none";
        if (carte.getLayoutProperty(couche.id, "visibility") !== visibiliteVoulue) {
          carte.setLayoutProperty(couche.id, "visibility", visibiliteVoulue);
        }
        if (
          carte.getPaintProperty(couche.id, "raster-opacity") !== opacites[couche.id]
        ) {
          carte.setPaintProperty(couche.id, "raster-opacity", opacites[couche.id]);
        }
      }
    }
  };

  /* Repli sur le composite précédent quand une tuile GIBS manque. */
  gererErreurRef.current = (evenement: unknown) => {
    const details = evenement as { sourceId?: string; error?: { status?: number } };
    const id = details.sourceId as IdCouche | undefined;
    if (!id || !COUCHES.some((couche) => couche.id === id)) {
      const message = (evenement as { error?: { message?: string } }).error?.message;
      if (message && /style/i.test(message)) {
        setErreurFond(
          "Le fond de carte n'a pas pu être chargé. Vérifiez la connexion puis réessayez.",
        );
      }
      return;
    }
    const maintenant = Date.now();
    if (maintenant - (dernierRepli.current[id] ?? 0) < 2_000) return;
    dernierRepli.current[id] = maintenant;

    const actuel = replisRef.current[id];
    if (actuel >= REPLIS_MAX) {
      setMessageRepli(
        `Aucune image ${TITRES_COUCHE[id]} disponible sur les ${REPLIS_MAX + 1} derniers composites.`,
      );
      return;
    }
    const suivant = actuel + 1;
    replisRef.current = { ...replisRef.current, [id]: suivant };
    setReplis(replisRef.current);
    setMessageRepli(
      `Image ${TITRES_COUCHE[id]} indisponible : repli sur le composite du ` +
        `${dateAffichee(ajouterJours(dateAligne, -PAS_COMPOSITE_JOURS * suivant))}.`,
    );
  };

  /* Clic sur la carte → /api/point/ → popup avec source et confiance. */
  gererClicRef.current = (evenement: maplibregl.MapMouseEvent) => {
    const carte = carteRef.current;
    if (!carte) return;
    const { lat, lng } = evenement.lngLat;

    popupRef.current?.remove();
    const popup = new maplibregl.Popup({
      maxWidth: "340px",
      className: "popup-carte",
      focusAfterOpen: false,
    })
      .setLngLat(evenement.lngLat)
      .setHTML(
        '<div class="popup-agrosentry"><p>Chargement des valeurs NASA POWER…</p></div>',
      )
      .addTo(carte);
    popupRef.current = popup;

    requeteRef.current?.abort();
    const controleur = new AbortController();
    requeteRef.current = controleur;

    getPoint(lat, lng, controleur.signal)
      .then((donnees) => {
        popup.setLngLat(evenement.lngLat).setHTML(htmlPoint(donnees));
      })
      .catch((erreur: unknown) => {
        if (erreur instanceof DOMException && erreur.name === "AbortError") return;
        popup.setHTML(htmlErreur(erreur));
      });
  };

  /* Création de la carte (une seule fois). */
  useEffect(() => {
    const conteneur = conteneurRef.current;
    if (!conteneur) return;

    const carte = new maplibregl.Map({
      container: conteneur,
      style: STYLES_FOND.clair as string,
      center: CENTRE,
      zoom: ZOOM_INITIAL,
      pitch: 55,
      bearing: -15,
      attributionControl: { compact: false },
    });
    carteRef.current = carte;

    carte.addControl(
      new maplibregl.NavigationControl({
        showCompass: true,
        visualizePitch: true,
      }),
      "bottom-right",
    );
    carte.addControl(new maplibregl.ScaleControl({ unit: "metric", maxWidth: 120 }));
    carte.addControl(new maplibregl.FullscreenControl());

    const appliquer = () => appliquerDesQuePretRef.current();
    const surErreur = (evenement: unknown) => gererErreurRef.current(evenement);
    const surClic = (evenement: maplibregl.MapMouseEvent) =>
      gererClicRef.current(evenement);

    carte.on("load", appliquer);
    carte.on("error", surErreur);
    carte.on("click", surClic);

    return () => {
      requeteRef.current?.abort();
      popupRef.current?.remove();
      carte.off("load", appliquer);
      carte.off("error", surErreur);
      carte.off("click", surClic);
      carte.remove();
      carteRef.current = null;
      urlsInstallees.current = {};
      terrainRef.current = null;
    };
  }, []);

  /* Changement de fond : le style est remplacé, il faut réinstaller les couches. */
  useEffect(() => {
    const carte = carteRef.current;
    if (!carte) return;
    if (premierFond.current) {
      premierFond.current = false;
      return;
    }
    urlsInstallees.current = {};
    terrainRef.current = null;
    setErreurFond(null);
    carte.setStyle(STYLES_FOND[fond]);
    appliquerDesQuePretRef.current();
  }, [fond]);

  /* Toute modification d'état réinstalle les couches concernées. */
  useEffect(() => {
    appliquerRef.current();
  }, [dateAligne, visibles, opacites, replis, mode3D]);

  /* Bascule 2D / 3D : inclinaison de la caméra et terrain. */
  useEffect(() => {
    const carte = carteRef.current;
    if (!carte) return;
    carte.easeTo({ pitch: mode3D ? 55 : 0, bearing: mode3D ? -15 : 0, duration: 600 });
    appliquerRef.current();
  }, [mode3D]);

  /* Bandeau hors-ligne. */
  useEffect(() => {
    const enLigne = () => setHorsLigne(false);
    const horsLigneEvenement = () => setHorsLigne(true);
    window.addEventListener("online", enLigne);
    window.addEventListener("offline", horsLigneEvenement);
    return () => {
      window.removeEventListener("online", enLigne);
      window.removeEventListener("offline", horsLigneEvenement);
    };
  }, []);

  const changerDate = (valeur: string) => {
    setReplis({ ndvi: 0, lst: 0, truecolor: 0 });
    replisRef.current = { ndvi: 0, lst: 0, truecolor: 0 };
    setMessageRepli(null);
    setDateChoisie(alignerDate(valeur || DATE_MIN));
  };

  return (
    <div className="carte-conteneur">
      <div ref={conteneurRef} className="carte-canvas" />

      <section className="carte-panneau carte-panneau-gauche" aria-label="Fond et date">
        <h1 className="carte-titre">AgroSentry — Bafia</h1>
        <div className="carte-boutons" role="group" aria-label="Fond de carte">
          {FONDS.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => setFond(option.id)}
              className={fond === option.id ? "actif" : ""}
              aria-pressed={fond === option.id}
            >
              {option.libelle}
            </button>
          ))}
        </div>

        <button
          type="button"
          className="carte-bouton-large"
          onClick={() => setMode3D((actuel) => !actuel)}
          aria-pressed={mode3D}
        >
          {mode3D ? "Passer en 2D" : "Passer en 3D"}
        </button>

        <label className="carte-champ">
          Date du composite
          <input
            type="date"
            value={dateChoisie}
            min={DATE_MIN}
            max={dateDuJour()}
            onChange={(evenement) => changerDate(evenement.target.value)}
          />
        </label>
        <p className="carte-aide">
          Composites de 8 jours. Archive GIBS disponible depuis le
          {" "}
          {dateAffichee(DATE_MIN)}. Date utilisée :{" "}
          <strong>{dateAffichee(dateAligne)}</strong>.
        </p>
        <p className="carte-source">
          Source raster : {ATTRIBUTION_GIBS}. Fond : {ATTRIBUTION_FOND}, Esri.
        </p>
        <p className="carte-demo">Démonstration — à valider avec un agronome.</p>
      </section>

      <section className="carte-panneau carte-panneau-droit" aria-label="Couches">
        <h2 className="carte-sous-titre">Couches NASA</h2>
        {COUCHES.map((couche) => {
          const dateCouche = ajouterJours(
            dateAligne,
            -PAS_COMPOSITE_JOURS * replis[couche.id],
          );
          return (
            <div key={couche.id} className="carte-couche">
              <label className="carte-case">
                <input
                  type="checkbox"
                  checked={visibles[couche.id]}
                  onChange={(evenement) =>
                    setVisibles((actuel) => ({
                      ...actuel,
                      [couche.id]: evenement.target.checked,
                    }))
                  }
                />
                {couche.nom}
              </label>
              <label className="carte-champ carte-champ-opacite">
                Opacité {Math.round(opacites[couche.id] * 100)} %
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={Math.round(opacites[couche.id] * 100)}
                  onChange={(evenement) =>
                    setOpacites((actuel) => ({
                      ...actuel,
                      [couche.id]: Number(evenement.target.value) / 100,
                    }))
                  }
                />
              </label>
              <p className="carte-legende-date">
                Composite du {dateAffichee(dateCouche)} · {couche.unite}
              </p>
              <div
                className="carte-legende"
                role="img"
                aria-label={`Légende ${couche.nom} : ${couche.legende
                  .map((entree) => entree.libelle)
                  .join(", ")}`}
              >
                {couche.legende.map((entree) => (
                  <span key={entree.libelle} className="carte-legende-item">
                    <span
                      className="carte-legende-puce"
                      style={{ backgroundColor: entree.couleur }}
                    />
                    {entree.libelle}
                  </span>
                ))}
              </div>
              <p className="carte-aide">{couche.description}</p>
            </div>
          );
        })}
      </section>

      {messageRepli && (
        <div className="carte-alerte carte-alerte-repli" role="status">
          {messageRepli}
        </div>
      )}

      {erreurFond && (
        <div className="carte-alerte carte-alerte-erreur" role="alert">
          {erreurFond}
        </div>
      )}

      {horsLigne && (
        <div className="carte-alerte carte-alerte-hors-ligne" role="status">
          Hors-ligne : les images et les valeurs peuvent être absentes. Les
          dernières données chargées restent affichées.
        </div>
      )}
    </div>
  );
}
