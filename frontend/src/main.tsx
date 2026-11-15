import React from "react";
import ReactDOM from "react-dom/client";
import "maplibre-gl/dist/maplibre-gl.css";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

/*
 * Le service worker n'est enregistré qu'en production : en développement il
 * mettrait en cache des fichiers obsolètes et pourrait afficher une page vide.
 */
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch((erreur) => {
      console.warn("Service worker non enregistré :", erreur);
    });
  });
}
