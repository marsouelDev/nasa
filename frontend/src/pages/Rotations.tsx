/**
 * Page « Rotations » : comparateur S0 / S1 / S2 piloté par des curseurs de
 * pondération, branché sur `/api/rotations/` (phase 3 du cahier des charges).
 */

import { useEffect, useMemo, useState } from "react";
import {
  estAnnulation,
  getRotations,
  messageErreur,
  type ReponseRotations,
  type ScenarioRotation,
} from "../api";

const ZONE = "bafia";

const PRIORITES = [
  { id: "eau", libelle: "Économie d'eau" },
  { id: "sol", libelle: "Protection du sol" },
  { id: "revenu", libelle: "Revenu" },
  { id: "travail", libelle: "Facilité de travail" },
] as const;

type IdPriorite = (typeof PRIORITES)[number]["id"];

const POIDS_INITIAUX: Record<IdPriorite, number> = {
  eau: 0.3,
  sol: 0.2,
  revenu: 0.2,
  travail: 0.2,
};

const LIBELLES_CRITERE: Record<string, string> = {
  economie_eau: "Économie d'eau",
  protection_erosion: "Protection contre l'érosion",
  matiere_organique: "Matière organique",
  azote: "Azote",
  rupture_ravageurs: "Rupture des ravageurs",
  revenu: "Revenu",
  facilite_travail: "Facilité de travail",
};

function libellePluie(facteur: number): string {
  if (facteur === 0) return "Pluie observée";
  const pourcentage = Math.round(facteur * 100);
  return pourcentage > 0
    ? `Pluie + ${pourcentage} %`
    : `Pluie ${pourcentage} %`;
}

function CarteScenario({
  scenario,
  meilleur,
}: {
  scenario: ScenarioRotation;
  meilleur: boolean;
}) {
  return (
    <article className="carte-scenario">
      <header>
        <h3>
          {scenario.id} — {scenario.nom}
        </h3>
        <p className="score">
          {scenario.score.toFixed(2)} <span>/ 10</span>
        </p>
        {meilleur && (
          <p className="etiquette-meilleur">Meilleur score comparé</p>
        )}
      </header>

      <p>{scenario.description}</p>
      <p>
        <strong>Parcours :</strong> {scenario.parcours.join(" → ")}
      </p>
      <p>
        <strong>Confiance :</strong> {scenario.confiance}
      </p>

      <table className="tableau">
        <caption>Notes par critère (0–10) et effet de la pluie</caption>
        <thead>
          <tr>
            <th scope="col">Scénario de pluie</th>
            <th scope="col">Score</th>
            <th scope="col">Confiance</th>
          </tr>
        </thead>
        <tbody>
          {scenario.evaluations_climatiques.map((evaluation) => (
            <tr key={`${scenario.id}-${evaluation.pluie_facteur}`}>
              <td>
                {evaluation.pluie_label ||
                  libellePluie(evaluation.pluie_facteur)}
              </td>
              <td>{evaluation.score.toFixed(2)}</td>
              <td>{evaluation.confiance}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <details>
        <summary>Détail des notes retenues</summary>
        <ul>
          {Object.entries(scenario.contributions).map(([critere, note]) => (
            <li key={critere}>
              {LIBELLES_CRITERE[critere] ?? critere} : {note.toFixed(1)} / 10
            </li>
          ))}
        </ul>
      </details>

      <details>
        <summary>Pourquoi cette proposition ?</summary>
        <p>{scenario.pourquoi_proposee}</p>
        <h4>Données à l'appui</h4>
        <ul>
          {scenario.donnees_a_l_appui.map((element) => (
            <li key={element}>{element}</li>
          ))}
        </ul>
        <h4>Bénéfices attendus</h4>
        <ul>
          {scenario.benefices.map((element) => (
            <li key={element}>{element}</li>
          ))}
        </ul>
        <h4>Lacunes d'information</h4>
        <ul>
          {scenario.lacunes_information.map((element) => (
            <li key={element}>{element}</li>
          ))}
        </ul>
        <h4>Risques à évaluer</h4>
        <ul>
          {scenario.risques_a_evaluer.map((element) => (
            <li key={element}>{element}</li>
          ))}
        </ul>
      </details>

      {scenario.a_valider_par_agronome && (
        <p className="page-avertissement">À valider avec un agronome.</p>
      )}
    </article>
  );
}

export default function Rotations() {
  const [poids, setPoids] =
    useState<Record<IdPriorite, number>>(POIDS_INITIAUX);
  const [pluiePersonnalisee, setPluiePersonnalisee] = useState(false);
  const [facteurPluie, setFacteurPluie] = useState(-0.3);
  const [donnees, setDonnees] = useState<ReponseRotations | null>(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  const totalPoids = useMemo(
    () => Object.values(poids).reduce((somme, valeur) => somme + valeur, 0),
    [poids],
  );

  useEffect(() => {
    const controleur = new AbortController();
    const minuteur = window.setTimeout(() => {
      setChargement(true);
      getRotations(
        {
          zone: ZONE,
          priorites: PRIORITES.map((priorite) => priorite.id),
          pondations: poids,
          pluie: pluiePersonnalisee ? facteurPluie : undefined,
        },
        controleur.signal,
      )
        .then((reponse) => {
          setDonnees(reponse);
          setErreur(null);
        })
        .catch((probleme: unknown) => {
          if (estAnnulation(probleme)) return;
          setErreur(messageErreur(probleme));
        })
        .finally(() => {
          if (!controleur.signal.aborted) setChargement(false);
        });
    }, 300);

    return () => {
      window.clearTimeout(minuteur);
      controleur.abort();
    };
  }, [poids, pluiePersonnalisee, facteurPluie]);

  const meilleurScore = donnees
    ? Math.max(...donnees.scenarios.map((scenario) => scenario.score))
    : null;

  return (
    <div className="page">
      <h2>Comparateur de rotations</h2>

      <section className="bloc-reglages" aria-label="Pondérations">
        <h3>Priorités de l'exploitation</h3>
        {PRIORITES.map((priorite) => (
          <label key={priorite.id} className="curseur">
            <span>
              {priorite.libelle} — poids {poids[priorite.id].toFixed(2)}
            </span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={poids[priorite.id]}
              onChange={(evenement) =>
                setPoids((actuel) => ({
                  ...actuel,
                  [priorite.id]: Number(evenement.target.value),
                }))
              }
            />
          </label>
        ))}
        <p className={totalPoids === 0 ? "page-erreur" : "page-note"}>
          Somme des poids : {totalPoids.toFixed(2)} (le score est une moyenne
          pondérée, les poids n'ont pas besoin de totaliser 1).
        </p>

        <label className="case">
          <input
            type="checkbox"
            checked={pluiePersonnalisee}
            onChange={(evenement) =>
              setPluiePersonnalisee(evenement.target.checked)
            }
          />
          Simuler une pluie personnalisée
        </label>

        {pluiePersonnalisee && (
          <label className="curseur">
            <span>Pluie : {libellePluie(facteurPluie)}</span>
            <input
              type="range"
              min={-0.5}
              max={0.5}
              step={0.05}
              value={facteurPluie}
              onChange={(evenement) =>
                setFacteurPluie(Number(evenement.target.value))
              }
            />
          </label>
        )}
      </section>

      {chargement && <p role="status">Calcul des scénarios…</p>}

      {erreur && (
        <p className="page-erreur" role="alert">
          {erreur}
        </p>
      )}

      {donnees && (
        <>
          <p className="page-source">
            Source : {donnees.source}
            {donnees.hypotheses_a_valider
              ? " · hypothèses de démonstration à valider."
              : ""}
          </p>
          <div className="grille-scenarios">
            {donnees.scenarios.map((scenario) => (
              <CarteScenario
                key={scenario.id}
                scenario={scenario}
                meilleur={scenario.score === meilleurScore}
              />
            ))}
          </div>
        </>
      )}

   
    </div>
  );
}
