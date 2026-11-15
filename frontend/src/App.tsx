/** Coquille de l'application : en-tête, navigation et page courante. */

import Carte from "./components/Carte";
import Tendances from "./pages/Tendances";
import Rotations from "./pages/Rotations";
import ConsoleSMS from "./pages/ConsoleSMS";

const LIENS = [
  { chemin: "/", libelle: "Carte" },
  { chemin: "/tendances", libelle: "Tendances" },
  { chemin: "/rotations", libelle: "Rotations" },
  { chemin: "/sms", libelle: "SMS / USSD" },
];

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
      <main className="app-contenu">{page}</main>
    </div>
  );
}
