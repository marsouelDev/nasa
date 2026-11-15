/** Coquille de l'application : en-tête, navigation et page courante. */

import { Suspense, lazy } from "react";

const Carte = lazy(() => import("./components/Carte"));
const Tendances = lazy(() => import("./pages/Tendances"));
const Rotations = lazy(() => import("./pages/Rotations"));
const ConsoleSMS = lazy(() => import("./pages/ConsoleSMS"));

const LIENS = [
  { chemin: "/", libelle: "Carte" },
  { chemin: "/tendances", libelle: "Tendances" },
  { chemin: "/rotations", libelle: "Rotations" },
  { chemin: "/sms", libelle: "SMS / USSD" },
];

function ChargementPage() {
  return (
    <p role="status" className="page-note">
      Chargement…
    </p>
  );
}

export default function App() {
  const chemin = (window.location.pathname.replace(/\/+$/, "") || "/") as string;

  let page = <Carte />;
  if (chemin === "/tendances") page = <Tendances />;
  else if (chemin === "/rotations") page = <Rotations />;
  else if (chemin === "/sms") page = <ConsoleSMS />;

  return (
    <div className="app">
      <header className="app-entete">
        <span className="app-marque">AgroSentry</span>
        <nav className="app-nav" aria-label="Navigation principale">
          {LIENS.map((lien) => (
            <a
              key={lien.chemin}
              href={lien.chemin}
              className={chemin === lien.chemin ? "actif" : ""}
              aria-current={chemin === lien.chemin ? "page" : undefined}
            >
              {lien.libelle}
            </a>
          ))}
        </nav>
      </header>
      <main className="app-contenu">
        <Suspense fallback={<ChargementPage />}>{page}</Suspense>
      </main>
    </div>
  );
}
