import { useEffect, useRef, useState } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";

const CENTRE: [number, number] = [11.23, 4.75];
const ZOOM_INITIAL = 11;
const DATE_MIN = "2025-02-12";

const STYLE_PLAN = "https://tiles.openmaplibre.org/styles/openfreemap/basic-v2";

const STYLE_SATELLITE: StyleSpecification = {
  version: 8,
  sources: {
    esri: {
      type: "raster",
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256,
      attribution: "Esri, Maxar, Earthstar Geographics",
    },
  },
  layers: [{ id: "esri", type: "raster", source: "esri" }],
};

function daysSinceMin(dateStr: string): number {
  const d = new Date(dateStr);
  const min = new Date(DATE_MIN);
  return Number(d.getTime() - min.getTime()) / 86400000;
}

function alignDate(dateStr: string): string {
  const d = new Date(dateStr);
  const min = new Date(DATE_MIN);
  if (d < min) { return DATE_MIN; }
  const offset = daysSinceMin(dateStr);
  const aligned = new Date(min);
  aligned.setDate(min.getDate() + Math.ceil(offset / 8) * 8);
  return aligned.toISOString().split("T")[0];
}

export default function Carte() {
  const conteneurRef = useRef<HTMLDivElement | null>(null);
  const carteRef = useRef<maplibregl.Map | null>(null);
  const [modele, setModele] = useState<"plan" | "satellite">("plan");
  const [date, setDate] = useState<string>(DATE_MIN);

  useEffect(() => {
    const conteneur = conteneurRef.current;
    if (!conteneur) return;
    const carte = new maplibregl.Map({
      container: conteneur,
      style: STYLE_PLAN,
      center: CENTRE,
      zoom: ZOOM_INITIAL,
      pitch: 60,
      bearing: -20,
    });
    carteRef.current = carte;
    carte.addControl(new maplibregl.NavigationControl({ showCompass: false }));
    carte.addControl(new maplibregl.ScaleControl({ unit: "metric" }));
    carte.addControl(new maplibregl.FullscreenControl());
    carte.on("load", () => {
      if (!carte.getSource("raster-dem")) {
        carte.addSource("raster-dem", {
          type: "raster-dem",
          tiles: ["https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png"],
          encoding: "terrarium",
          maxzoom: 15,
        });
        carte.setTerrain({ source: "raster-dem", exaggeration: 1.5 });
        carte.addLayer({ id: "relief", type: "hillshade", source: "raster-dem" });
      }
    });
    return () => { carte.remove(); carteRef.current = null; };
  }, []);

  useEffect(() => {
    const carte = carteRef.current;
    if (!carte) return;
    carte.setStyle(modele === "plan" ? STYLE_PLAN : STYLE_SATELLITE);
  }, [modele]);

  useEffect(() => {
    setDate(alignDate(date));
  }, [date]);

  useEffect(() => {
    const carte = carteRef.current;
    if (!carte) return;
    // Couche NDVI (maxzoom 9)
    const alignedStr = alignDate(date);
    if (carte.getLayer("ndvi")) carte.removeLayer("ndvi");
    if (carte.getSource("ndvi")) carte.removeSource("ndvi");
    carte.addSource("ndvi", {
      type: "raster",
      tiles: [`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_NDVI_8Day/default/${alignedStr}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png`],
    });
    carte.addLayer({
      id: "ndvi",
      type: "raster",
      source: "ndvi",
      paint: { "raster-opacity": 0.8 },
    });
  }, [date]);

  useEffect(() => {
    const carte = carteRef.current;
    if (!carte) return;
    // Couleur vraie (maxzoom 9)
    const alignedStr = alignDate(date);
    if (carte.getLayer("truecolor")) carte.removeLayer("truecolor");
    if (carte.getSource("truecolor")) carte.removeSource("truecolor");
    carte.addSource("truecolor", {
      type: "raster",
      tiles: [`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${alignedStr}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png`],
    });
    carte.addLayer({
      id: "truecolor",
      type: "raster",
      source: "truecolor",
      paint: { "raster-opacity": 0.8 },
    });
  }, [date]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div ref={conteneurRef} style={{ width: "100%", height: "100vh" }} />
      <div
        style={{
          position: "absolute",
          top: 12,
          left: 12,
          display: "flex",
          gap: 8,
        }}
      >
        <button onClick={() => setModele("plan")}>Plan</button>
        <button onClick={() => setModele("satellite")}>Satellite</button>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 12,
          left: 12,
          background: "rgba(255,255,255,0.9)",
          padding: "8px 12px",
          borderRadius: 8,
          fontSize: 13,
        }}
      >
        NDVI du {date} — GIBS (date bornée 12/02/2025, snap 8 jours)
      </div>
    </div>
  );
}