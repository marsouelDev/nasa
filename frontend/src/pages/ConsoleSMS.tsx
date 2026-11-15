/**
 * Page « SMS / USSD » : console de démonstration branchée sur l'API phase 5.
 *
 * Aucun message réel n'est envoyé : la passerelle est simulée côté backend
 * tant que les clés ne sont pas configurées. Les SMS ne sont préparés que
 * pour les agriculteurs ayant donné un consentement explicite (STOP pour se
 * désinscrire).
 */

import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  estAnnulation,
  getApercuSMS,
  getInscriptions,
  getJournalSMS,
  messageErreur,
  postAlertes,
  postDesinscription,
  postInscription,
  postSimulerSMS,
  postSimulerUssd,
  urlApi,
  type JournalSMS,
  type ReponseUssd,
  type ResumeInscriptions,
} from "../api";

const ZONE = "bafia";
const LONGUEUR_MAX = 160;
const ENTETE = "AgroSentry : ";

type Notice = { type: "ok" | "erreur" | "info"; texte: string } | null;

function maintenant(): string {
  return new Date().toLocaleString("fr-FR", {
    dateStyle: "short",
    timeStyle: "medium",
  });
}

export default function ConsoleSMS() {
  // Inscription
  const [telephone, setTelephone] = useState("+237600000000");
  const [nom, setNom] = useState("");
  const [langue, setLangue] = useState<"fr" | "en">("fr");
  const [consentement, setConsentement] = useState(false);
  const [resume, setResume] = useState<ResumeInscriptions | null>(null);
  const [noticeCompte, setNoticeCompte] = useState<Notice>(null);

  // SMS
  const [message, setMessage] = useState("");
  const [avecEntete, setAvecEntete] = useState(true);
  const [noticeSms, setNoticeSms] = useState<Notice>(null);
  const [journal, setJournal] = useState<JournalSMS | null>(null);
  const [chargementJournal, setChargementJournal] = useState(false);

  // USSD
  const [saisieUssd, setSaisieUssd] = useState("");
  const [reponseUssd, setReponseUssd] = useState<ReponseUssd | null>(null);
  const [noticeUssd, setNoticeUssd] = useState<Notice>(null);

  const texteComplet = avecEntete ? `${ENTETE}${message}` : message;
  const longueur = texteComplet.length;
  const tropLong = longueur > LONGUEUR_MAX;

  const chargerResume = useCallback(async () => {
    try {
      setResume(await getInscriptions());
    } catch {
      // optionnel en démo
    }
  }, []);

  const chargerJournal = useCallback(async () => {
    setChargementJournal(true);
    try {
      setJournal(await getJournalSMS(20));
    } catch (erreur) {
      if (!estAnnulation(erreur)) {
        setNoticeSms({ type: "erreur", texte: messageErreur(erreur) });
      }
    } finally {
      setChargementJournal(false);
    }
  }, []);

  useEffect(() => {
    void chargerResume();
    void chargerJournal();
  }, [chargerResume, chargerJournal]);

  const inscrire = async () => {
    setNoticeCompte(null);
    try {
      const reponse = await postInscription({
        telephone,
        zone: ZONE,
        langue,
        nom: nom || undefined,
        consentement,
      });
      setNoticeCompte({
        type: "ok",
        texte: `${reponse.message} Numéro ${reponse.agriculteur.telephone_masque}, consentement ${reponse.agriculteur.consentement_version} enregistré le ${reponse.agriculteur.consentement_le ?? ""}.`,
      });
      await chargerResume();
    } catch (erreur) {
      setNoticeCompte({ type: "erreur", texte: messageErreur(erreur) });
    }
  };

  const desinscrire = async () => {
    setNoticeCompte(null);
    try {
      const reponse = await postDesinscription(telephone);
      setNoticeCompte({ type: reponse.desinscrit ? "ok" : "info", texte: reponse.message });
      await chargerResume();
    } catch (erreur) {
      setNoticeCompte({ type: "erreur", texte: messageErreur(erreur) });
    }
  };

  const preRemplirDepuisApercu = async () => {
    setNoticeSms(null);
    try {
      const apercu = await getApercuSMS(ZONE, langue);
      if (!apercu.disponible) {
        setNoticeSms({
          type: "erreur",
          texte: "Risque indisponible pour cette zone : message impossible à construire.",
        });
        return;
      }
      const sansEntete = apercu.message.startsWith(ENTETE)
        ? apercu.message.slice(ENTETE.length)
        : apercu.message;
      setMessage(sansEntete.slice(0, LONGUEUR_MAX - (avecEntete ? ENTETE.length : 0)));
      setNoticeSms({
        type: "info",
        texte: `Aperçu généré depuis l'API (${apercu.longueur}/${apercu.longueur_max} car., source ${apercu.risque.source ?? "—"}).`,
      });
    } catch (erreur) {
      if (!estAnnulation(erreur)) {
        setNoticeSms({ type: "erreur", texte: messageErreur(erreur) });
      }
    }
  };

  const simulerEnvoi = async () => {
    setNoticeSms(null);
    if (tropLong) return;
    try {
      const reponse = await postSimulerSMS(telephone, texteComplet.trim() || undefined);
      setNoticeSms({
        type: "ok",
        texte: `${reponse.message_utilisateur} (${reponse.sms.telephone_masque}, ${reponse.sms.longueur} car., statut ${reponse.sms.statut}).`,
      });
      setMessage("");
      await chargerJournal();
    } catch (erreur) {
      if (erreur instanceof ApiError && (erreur.statut === 400 || erreur.statut === 403)) {
        setNoticeSms({ type: "erreur", texte: messageErreur(erreur) });
      } else if (!estAnnulation(erreur)) {
        setNoticeSms({ type: "erreur", texte: messageErreur(erreur) });
      }
    }
  };

  const declencherAlertes = async () => {
    setNoticeSms(null);
    try {
      const reponse = await postAlertes(ZONE);
      setNoticeSms({
        type: "ok",
        texte: `Tâche ${reponse.task_id} exécutée (eager). Alertes préparées : ${reponse.resultat.alertes}, envois créés : ${reponse.resultat.envoies_crees}.`,
      });
      await chargerJournal();
    } catch (erreur) {
      setNoticeSms({ type: "erreur", texte: messageErreur(erreur) });
    }
  };

  const simulerUssd = async (text?: string) => {
    setNoticeUssd(null);
    try {
      const reponse = await postSimulerUssd(text ?? saisieUssd, ZONE);
      setReponseUssd(reponse);
    } catch (erreur) {
      if (!estAnnulation(erreur)) {
        setNoticeUssd({ type: "erreur", texte: messageErreur(erreur) });
      }
    }
  };

  const noticeBloc = (notice: Notice) =>
    notice ? (
      <p className={notice.type === "erreur" ? "page-erreur" : "page-note"} role={notice.type === "erreur" ? "alert" : "status"}>
        {notice.texte}
      </p>
    ) : null;

  return (
    <div className="page">
      <h2>Console SMS / USSD (simulation phase 5)</h2>
      <p className="page-note">
        Démonstration : aucun SMS réel n'est envoyé et aucun réseau mobile n'est
        contacté. Les SMS ne sont préparés que pour les numéros avec consentement
        explicite enregistré. API {urlApi()}.
      </p>

      <section className="bloc-reglages" aria-label="Inscription et consentement">
        <h3>Inscription et consentement</h3>
        <p className="page-note">
          {resume
            ? `${resume.nombre_agriculteurs} agriculteur(s), ${resume.nombre_consentants} consentant(s). Version du consentement : ${resume.version_consentement}.`
            : "Chargement du résumé…"}
        </p>
        {resume && <p className="page-note">Texte : {resume.texte_consentement}</p>}

        <label className="champ">
          Numéro de téléphone
          <input
            type="tel"
            value={telephone}
            onChange={(e) => setTelephone(e.target.value)}
            placeholder="+2376XXXXXXXX"
          />
        </label>
        <label className="champ">
          Nom (optionnel)
          <input type="text" value={nom} onChange={(e) => setNom(e.target.value)} />
        </label>
        <label className="champ">
          Langue
          <select value={langue} onChange={(e) => setLangue(e.target.value as "fr" | "en")}>
            <option value="fr">Français</option>
            <option value="en">English</option>
          </select>
        </label>
        <label className="case">
          <input
            type="checkbox"
            checked={consentement}
            onChange={(e) => setConsentement(e.target.checked)}
          />
          Je donne mon consentement explicite pour recevoir des SMS d'alerte AgroSentry
          sur ce numéro (date et version enregistrées). Je peux répondre STOP pour me
          désinscrire.
        </label>
        <div className="barre-boutons">
          <button type="button" className="bouton-principal" onClick={() => void inscrire()}>
            Inscrire / mettre à jour
          </button>
          <button type="button" onClick={() => void desinscrire()}>
            Se désinscrire (STOP)
          </button>
        </div>
        {noticeBloc(noticeCompte)}
      </section>

      <section className="bloc-reglages" aria-label="Envoi de SMS simulé">
        <h3>SMS simulé (≤ {LONGUEUR_MAX} caractères)</h3>
        <label className="champ">
          Message
          <textarea
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Laissez vide pour générer le message de risque depuis l'API."
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
            onChange={(e) => setAvecEntete(e.target.checked)}
          />
          Ajouter l'en-tête « {ENTETE.trim()} »
        </label>
        <div className="barre-boutons">
          <button type="button" onClick={() => void preRemplirDepuisApercu()}>
            Pré-remplir depuis /api/sms/apercu/
          </button>
          <button
            type="button"
            className="bouton-principal"
            onClick={() => void simulerEnvoi()}
            disabled={tropLong}
          >
            Simuler l'envoi (API)
          </button>
          <button type="button" onClick={() => void declencherAlertes()}>
            Déclencher alertes de risque (Celery eager)
          </button>
          <button type="button" onClick={() => void chargerJournal()} disabled={chargementJournal}>
            Rafraîchir le journal
          </button>
        </div>
        {noticeBloc(noticeSms)}
      </section>

      <section className="bloc-reglages" aria-label="USSD simulé">
        <h3>USSD simulé (≤ 182 caractères)</h3>
        <p className="page-note">
          Menu court : 1 risque, 2 pluie 30j, 3 calendrier de semis, 4 quitter.
          Réponses CON/END comme Africa's Talking, aucun réseau mobile.
        </p>
        <div className="barre-boutons">
          <button type="button" onClick={() => void simulerUssd("")}>Afficher le menu</button>
          <button type="button" onClick={() => void simulerUssd("1")}>1 Risque</button>
          <button type="button" onClick={() => void simulerUssd("2")}>2 Pluie</button>
          <button type="button" onClick={() => void simulerUssd("3")}>3 Semis</button>
          <button type="button" onClick={() => void simulerUssd("4")}>4 Quitter</button>
        </div>
        <label className="champ">
          Saisie libre
          <input
            type="text"
            value={saisieUssd}
            onChange={(e) => setSaisieUssd(e.target.value)}
            placeholder="ex. 1, *384*2#"
          />
        </label>
        <button type="button" onClick={() => void simulerUssd()}>Envoyer la saisie</button>
        {noticeBloc(noticeUssd)}
        {reponseUssd && (
          <pre className="ecran-ussd" aria-live="polite">
            {reponseUssd.reponse}
            {"\n"}
            — {reponseUssd.longueur}/{reponseUssd.longueur_max} car., {reponseUssd.source}, zone{" "}
            {reponseUssd.zone.nom}
          </pre>
        )}
      </section>

      <section aria-label="Journal des SMS">
        <h3>Journal des SMS ({journal?.envois.length ?? 0})</h3>
        <p className="page-note">
          {journal
            ? `Source ${journal.source}. Simulation ${journal.simulation ? "active" : "inactive"} (aucun envoi réel sans configuration explicite).`
            : "Journal non chargé."}
        </p>
        {!journal || journal.envois.length === 0 ? (
          <p className="page-note">Aucun envoi enregistré pour le moment.</p>
        ) : (
          <ul className="journal-sms">
            {journal.envois.map((entree) => (
              <li key={entree.id}>
                <p className="journal-entete">
                  {entree.cree_le ? new Date(entree.cree_le).toLocaleString("fr-FR") : maintenant()} ·{" "}
                  {entree.telephone_masque} · {entree.longueur} caractères · {entree.statut} ·{" "}
                  {entree.categorie}
                </p>
                <p>{entree.message}</p>
                <p className="journal-demo">
                  Mode {entree.mode} — {entree.statut === "simule" ? "message non transmis." : entree.statut}.
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
