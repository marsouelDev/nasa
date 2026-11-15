/**
 * Client HTTP unique des appels à l'API AgroSentry.
 *
 * L'URL de base vient de `VITE_API_URL` (voir `frontend/.env.example`) et
 * retombe sur le serveur Django de développement. Toutes les erreurs réseau
 * ou HTTP sont converties en `ApiError` afin que les pages affichent un
 * message lisible plutôt qu'une page vide.
 */

const BASE_API = (
  import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api"
).replace(/\/+$/, "");

/** Erreur normalisée : `statut` vaut 0 quand le serveur est injoignable. */
export class ApiError extends Error {
  readonly statut: number;

  constructor(message: string, statut: number) {
    super(message);
    this.name = "ApiError";
    this.statut = statut;
  }
}

type OptionsRequete = {
  signal?: AbortSignal;
  method?: string;
  body?: unknown;
};

async function requete<T>(chemin: string, options: OptionsRequete = {}): Promise<T> {
  let reponse: Response;
  try {
    reponse = await fetch(`${BASE_API}${chemin}`, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch (erreur) {
    if (erreur instanceof DOMException && erreur.name === "AbortError") {
      throw erreur;
    }
    throw new ApiError(
      `API injoignable (${BASE_API}). Vérifiez que le serveur Django écoute sur le port 8000.`,
      0,
    );
  }

  if (!reponse.ok) {
    let message = `Erreur HTTP ${reponse.status}`;
    try {
      const corps: unknown = await reponse.json();
      if (corps && typeof corps === "object") {
        const detail = (corps as Record<string, unknown>).detail;
        const messageApi = (corps as Record<string, unknown>).message;
        if (typeof detail === "string") message = detail;
        else if (typeof messageApi === "string") message = messageApi;
      }
    } catch {
      // Corps non JSON : on garde le message générique.
    }
    throw new ApiError(message, reponse.status);
  }

  return (await reponse.json()) as T;
}

/** URL de base affichée dans l'interface (transparence sur la source). */
export function urlApi(): string {
  return BASE_API;
}

/** Vrai si la requête a été annulée volontairement (changement de page, etc.). */
export function estAnnulation(erreur: unknown): boolean {
  return erreur instanceof DOMException && erreur.name === "AbortError";
}

/** Message lisible pour l'utilisateur, quelle que soit l'erreur levée. */
export function messageErreur(erreur: unknown): string {
  if (erreur instanceof ApiError) return erreur.message;
  if (erreur instanceof Error) return erreur.message;
  return "Erreur inattendue.";
}

export interface Zone {
  slug: string;
  nom: string;
  latitude: number;
  longitude: number;
  [cle: string]: unknown;
}

export interface Risque {
  disponible: boolean;
  niveau: string | null;
  score?: number;
  confiance: string;
  source: string;
  explication?: string;
  message?: string;
  date_derniere_donnee?: string;
  modele?: { nom?: string; version?: string };
  a_valider_par_agronome?: boolean;
}

export interface Tendance {
  annee_courante: number;
  annees_reference: number[];
  labels: string[];
  pluie_courante_mm: Array<number | null>;
  pluie_moyenne_reference_mm: Array<number | null>;
  temp_courante_c: Array<number | null>;
  temp_moyenne_reference_c: Array<number | null>;
}

export interface ReponseTendances {
  zone: Zone;
  disponible: boolean;
  source: string;
  unite: Record<string, string>;
  derniere_donnee?: string;
  message?: string;
  tendance?: Tendance;
}

export interface EvaluationClimatique {
  pluie_facteur: number;
  pluie_label: string;
  score: number;
  contributions: Record<string, number>;
  confiance: string;
}

export interface ScenarioRotation {
  id: string;
  nom: string;
  parcours: string[];
  description: string;
  score: number;
  contributions: Record<string, number>;
  pourquoi_proposee: string;
  donnees_a_l_appui: string[];
  benefices: string[];
  lacunes_information: string[];
  risques_a_evaluer: string[];
  confiance: string;
  evaluations_climatiques: EvaluationClimatique[];
  a_valider_par_agronome: boolean;
}

export interface ReponseRotations {
  zone: Zone | null;
  source: string;
  hypotheses_a_valider: boolean;
  priorites: string[];
  pluie_facteur: number;
  scenarios: ScenarioRotation[];
}

export interface MeteoResume {
  disponible: boolean;
  derniere_date?: string;
  jours_couverts?: number;
  pluie_7j_mm?: number | null;
  pluie_30j_mm?: number | null;
  temp_max_moyenne_30j_c?: number | null;
  message?: string;
}

export interface ReponsePoint {
  position: { latitude: number; longitude: number };
  zone: Zone;
  distance_km: number;
  resolution: string;
  disponible: boolean;
  source: string;
  date_derniere_donnee: string | null;
  meteo: MeteoResume;
  risque: Risque;
  calendrier_semis: { annee: number; confiance: string };
  rotation: ReponseRotations;
  rotation_source?: string;
  avertissement: string;
}

export interface ParametresRotations {
  zone?: string;
  priorites: string[];
  pondations: Record<string, number>;
  pluie?: number;
}

/** Série mensuelle : année en cours vs moyenne des N années de référence. */
export function getTendances(
  zone: string,
  anneesReference = 10,
  signal?: AbortSignal,
): Promise<ReponseTendances> {
  const parametres = new URLSearchParams({
    zone,
    annees_reference: String(anneesReference),
  });
  return requete<ReponseTendances>(`/pluie/tendances/?${parametres}`, { signal });
}

/** Comparateur de rotations S0/S1/S2 avec priorités et pondérations. */
export function getRotations(
  parametres: ParametresRotations,
  signal?: AbortSignal,
): Promise<ReponseRotations> {
  const recherche = new URLSearchParams();
  if (parametres.zone) recherche.set("zone", parametres.zone);
  if (parametres.priorites.length > 0) {
    recherche.set("priorites", parametres.priorites.join(","));
  }
  const pondations = Object.entries(parametres.pondations)
    .filter(([, poids]) => Number.isFinite(poids))
    .map(([categorie, poids]) => `${categorie}=${poids}`)
    .join(",");
  if (pondations) recherche.set("pondations", pondations);
  if (typeof parametres.pluie === "number" && parametres.pluie !== 0) {
    recherche.set("pluie", String(parametres.pluie));
  }
  return requete<ReponseRotations>(`/rotations/?${recherche}`, { signal });
}

/** Valeurs météo et risque de la maille POWER la plus proche d'un point. */
export function getPoint(
  latitude: number,
  longitude: number,
  signal?: AbortSignal,
): Promise<ReponsePoint> {
  const parametres = new URLSearchParams({
    lat: latitude.toFixed(4),
    lon: longitude.toFixed(4),
  });
  return requete<ReponsePoint>(`/point/?${parametres}`, { signal });
}

/** Risque de sécheresse de la zone (règle ou Random Forest selon le backend). */
export interface ReponseRisques extends Risque {
  zone: Zone;
  culture: string;
}

export function getRisques(zone: string, signal?: AbortSignal): Promise<ReponseRisques> {
  return requete<ReponseRisques>(`/risques/?zone=${encodeURIComponent(zone)}`, {
    signal,
  });
}

// --- Phase 5 : comptes, SMS et USSD ---

export interface AgriculteurPublic {
  id: number;
  telephone_masque: string;
  nom: string;
  zone: string;
  zone_nom: string;
  langue: string;
  consentement: boolean;
  consentement_le: string | null;
  consentement_version: string;
  desinscrit_le: string | null;
  actif: boolean;
  peut_recevoir_sms: boolean;
  cree_le: string;
}

export interface ResumeInscriptions {
  nombre_agriculteurs: number;
  nombre_consentants: number;
  texte_consentement: string;
  version_consentement: string;
  langues: { code: string; libelle: string }[];
}

export interface ReponseInscription {
  cree: boolean;
  consentement_enregistre: boolean;
  version_consentement: string;
  agriculteur: AgriculteurPublic;
  message: string;
}

export interface ReponseStatutInscription {
  connu: boolean;
  agriculteur?: AgriculteurPublic;
  telephone_masque?: string;
  message?: string;
}

export interface ReponseDesinscription {
  connu: boolean;
  desinscrit: boolean;
  deja_desinscrit?: boolean;
  telephone_masque?: string;
  desinscrit_le?: string | null;
  consentement?: boolean;
  message: string;
}

export interface EnvoiJournal {
  id: number;
  telephone_masque: string;
  message: string;
  longueur: number;
  statut: string;
  mode: string;
  categorie: string;
  reference: string;
  cree_le: string;
}

export interface JournalSMS {
  simulation: boolean;
  longueur_max: number;
  source: string;
  genere_le: string;
  envois: EnvoiJournal[];
}

export interface ApercuSMS {
  zone: { slug: string; nom: string };
  langue: string;
  disponible: boolean;
  risque: { niveau: string | null; score?: number; confiance?: string; source?: string };
  message: string;
  longueur: number;
  longueur_max: number;
  source_sms: string;
  simulation: boolean;
  a_valider_par_agronome: boolean;
}

export interface ReponseSimulationSMS {
  envoye: boolean;
  simulation: boolean;
  longueur_max: number;
  sms: {
    id: number;
    telephone_masque: string;
    message: string;
    longueur: number;
    statut: string;
    mode: string;
    categorie: string;
    cree_le: string;
  };
  message_utilisateur: string;
}

export interface ResultatAlertes {
  task_id: string;
  simulation: boolean;
  zone: string | null;
  resultat: { zones: unknown[]; alertes: number; envoies_crees: number; ignores: unknown[] };
}

export interface ReponseUssd {
  reponse: string;
  longueur: number;
  longueur_max: number;
  simulation: boolean;
  zone: { slug: string; nom: string };
  source: string;
}

export function getInscriptions(): Promise<ResumeInscriptions> {
  return requete<ResumeInscriptions>("/inscriptions/");
}

export function getStatutInscription(telephone: string): Promise<ReponseStatutInscription> {
  return requete<ReponseStatutInscription>(
    `/inscriptions/statut/?telephone=${encodeURIComponent(telephone)}`,
  );
}

export function postInscription(data: {
  telephone: string;
  zone?: string;
  langue?: string;
  nom?: string;
  consentement: boolean;
}): Promise<ReponseInscription> {
  return requete<ReponseInscription>("/inscriptions/", { method: "POST", body: data });
}

export function postDesinscription(telephone: string): Promise<ReponseDesinscription> {
  return requete<ReponseDesinscription>("/desinscription/", {
    method: "POST",
    body: { telephone },
  });
}

export function getApercuSMS(zone = "bafia", langue = "fr"): Promise<ApercuSMS> {
  return requete<ApercuSMS>(
    `/sms/apercu/?zone=${encodeURIComponent(zone)}&langue=${encodeURIComponent(langue)}`,
  );
}

export function postSimulerSMS(telephone: string, message?: string): Promise<ReponseSimulationSMS> {
  const body: { telephone: string; message?: string } = { telephone };
  if (message && message.trim()) body.message = message;
  return requete<ReponseSimulationSMS>("/sms/simuler/", { method: "POST", body });
}

export function getJournalSMS(limite = 20): Promise<JournalSMS> {
  return requete<JournalSMS>(`/sms/journal/?limite=${limite}`);
}

export function postAlertes(zone?: string): Promise<ResultatAlertes> {
  const suffixe = zone ? `?zone=${encodeURIComponent(zone)}` : "";
  return requete<ResultatAlertes>(`/sms/alertes/${suffixe}`, { method: "POST", body: {} });
}

export function postSimulerUssd(text: string, zone = "bafia"): Promise<ReponseUssd> {
  return requete<ReponseUssd>(`/sms/ussd/simuler/?zone=${encodeURIComponent(zone)}`, {
    method: "POST",
    body: { text },
  });
}
