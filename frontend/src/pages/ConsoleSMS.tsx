/**
 * Page « SMS / USSD » : simulateur local.
 *
 * Aucun message n'est réellement envoyé (pas de passerelle SMS branchée avant
 * la phase 5) : tout est étiqueté « démonstration ». La longueur du message est
 * contrôlée à 160 caractères, comme un SMS simple.
 */

import { useEffect, useRef, useState } from "react";
import {
  estAnnulation,
  getRisques,
  messageErreur,
  urlApi,
} from "../api";

const ZONE = "bafia";
const LONGUEUR_MAX = 160;
const ENTETE = "AgroSentry : ";

interface SmsEnvoye {
  id: number;
  numero: string;
  texte: string;
  longueur: number;
  heure: string;
}

function maintenant(): string {
  return new Date().toLocaleString("fr-FR", {
    dateStyle: "short",
    timeStyle: "medium",
  });
}

export default function ConsoleSMS() {
  const [numero, setNumero] = useState("+237600000000");
  const [message, setMessage] = useState("");
  const [avecEntete, setAvecEntete] = useState(true);
  const [journal, setJournal] = useState<SmsEnvoye[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [codeUssd, setCodeUssd] = useState("*384*1#");
  const [sessionUssd, setSessionUssd] = useState<string | null>(null);
  const compteur = useRef(0);
  const requete = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => requete.current?.abort();
  }, []);

  const texteComplet = avecEntete ? `${ENTETE}${message}` : message;
  const longueur = texteComplet.length;
  const tropLong = longueur > LONGUEUR_MAX;
  const numeroValide = /^\+?[0-9 ]{8,17}$/.test(numero.trim());

  const preRemplirDepuisRisque = () => {
    requete.current?.abort();
    const controleur = new AbortController();
    requete.current = controleur;
    setErreur(null);
    getRisques(ZONE, controleur.signal)
      .then((risque) => {
        if (!risque.disponible) {
          setErreur(risque.message ?? "Risque indisponible pour cette zone.");
          return;
        }
        const score =
          typeof risque.score === "number"
            ? `${Math.round(risque.score * 100)} %`
            : "non calculé";
        const proposition =
          `Risque de sécheresse ${risque.niveau ?? "inconnu"} (${score}). ` +
          `Confiance ${risque.confiance}. À valider avec un agronome.`;
        setMessage(proposition.slice(0, LONGUEUR_MAX - ENTETE.length));
      })
      .catch((probleme: unknown) => {
        if (estAnnulation(probleme)) return;
        setErreur(messageErreur(probleme));
      });
  };

  const envoyer = () => {
    if (!numeroValide || message.trim() === "" || tropLong) return;
    compteur.current += 1;
    setJournal((actuel) => [
      {
        id: compteur.current,
        numero: numero.trim(),
        texte: texteComplet,
        longueur,
        heure: maintenant(),
      },
      ...actuel,
    ]);
    setMessage("");
  };

  const composerUssd = () => {
    setSessionUssd(
      [
        "AgroSentry (simulation USSD)",
        `Code composé : ${codeUssd}`,
        "1. Risque de sécheresse",
        "2. Fenêtre de semis",
        "3. Comparateur de rotations",
        "Répondez par un chiffre (démonstration, aucun réseau utilisé).",
      ].join("\n"),
    );
  };

  return (
    <div className="page">
      <h2>Simulateur SMS / USSD</h2>
      <p className="page-note">
        Démonstration : aucun SMS n'est envoyé, aucun réseau mobile n'est
        contacté. API {urlApi()}.
      </p>

      <section className="bloc-reglages" aria-label="Envoi de SMS simulé">
        <label className="champ">
          Numéro de téléphone
          <input
            type="tel"
            value={numero}
            onChange={(evenement) => setNumero(evenement.target.value)}
            placeholder="+2376XXXXXXXX"
            aria-invalid={!numeroValide}
          />
        </label>
        {!numeroValide && (
          <p className="page-erreur" role="alert">
            Numéro invalide : 8 à 17 chiffres, éventuellement précédés de « + ».
          </p>
        )}

        <label className="champ">
          Message
          <textarea
            rows={4}
            value={message}
            onChange={(evenement) => setMessage(evenement.target.value)}
            placeholder="Ex. : Risque de sécheresse élevé, retarder le semis de 7 jours."
            aria-describedby="compteur-sms"
          />
        </label>

        <p
          id="compteur-sms"
          className={tropLong ? "page-erreur" : "page-note"}
          role={tropLong ? "alert" : undefined}
        >
          {longueur} / {LONGUEUR_MAX} caractères
          {tropLong ? " — message trop long pour un SMS simple." : ""}
        </p>

        <label className="case">
          <input
            type="checkbox"
            checked={avecEntete}
            onChange={(evenement) => setAvecEntete(evenement.target.checked)}
          />
          Ajouter l'en-tête « {ENTETE.trim()} »
        </label>

        <div className="barre-boutons">
          <button type="button" onClick={preRemplirDepuisRisque}>
            Pré-remplir depuis /api/risques/
          </button>
          <button
            type="button"
            className="bouton-principal"
            onClick={envoyer}
            disabled={!numeroValide || message.trim() === "" || tropLong}
          >
            Envoyer (simulation)
          </button>
        </div>

        {erreur && (
          <p className="page-erreur" role="alert">
            {erreur}
          </p>
        )}
      </section>

      <section className="bloc-reglages" aria-label="USSD simulé">
        <h3>USSD (simulation)</h3>
        <label className="champ">
          Code USSD
          <input
            type="text"
            value={codeUssd}
            onChange={(evenement) => setCodeUssd(evenement.target.value)}
          />
        </label>
        <button type="button" onClick={composerUssd}>
          Composer le code
        </button>
        {sessionUssd && (
          <pre className="ecran-ussd" aria-live="polite">
            {sessionUssd}
          </pre>
        )}
      </section>

      <section aria-label="Journal des envois simulés">
        <h3>Journal des envois simulés ({journal.length})</h3>
        {journal.length === 0 ? (
          <p className="page-note">Aucun message simulé pour le moment.</p>
        ) : (
          <ul className="journal-sms">
            {journal.map((entree) => (
              <li key={entree.id}>
                <p className="journal-entete">
                  {entree.heure} · {entree.numero} · {entree.longueur} caractères
                </p>
                <p>{entree.texte}</p>
                <p className="journal-demo">
                  Démonstration — message non transmis.
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
