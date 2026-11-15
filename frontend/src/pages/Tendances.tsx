/**
 * Page « Tendances » : pluie et température de l'année en cours comparées
 * à la moyenne des N années précédentes (données NASA POWER via l'API).
 */

import { useEffect, useState } from "react";
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
  type ChartData,
  type ChartOptions,
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";
import {
  estAnnulation,
  getTendances,
  messageErreur,
  urlApi,
  type ReponseTendances,
  type Tendance,
} from "../api";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Filler,
  Title,
  Tooltip,
  Legend,
);

const ZONE = "bafia";
const ANNEES_REFERENCE = 10;

const OPTIONS_PLUIE: ChartOptions<"bar"> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: "bottom" },
    title: { display: true, text: "Pluie mensuelle cumulée (mm/mois)" },
    tooltip: {
      callbacks: {
        label: (contexte) =>
          `${contexte.dataset.label} : ${contexte.formattedValue} mm`,
      },
    },
  },
  scales: {
    y: { beginAtZero: true, title: { display: true, text: "mm/mois" } },
  },
};

const OPTIONS_TEMPERATURE: ChartOptions<"line"> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: "bottom" },
    title: { display: true, text: "Température maximale moyenne (°C)" },
    tooltip: {
      callbacks: {
        label: (contexte) =>
          `${contexte.dataset.label} : ${contexte.formattedValue} °C`,
      },
    },
  },
  scales: {
    y: { title: { display: true, text: "°C" } },
  },
};

function libelleReference(annees: number[]): string {
  if (annees.length === 0) return "Moyenne de référence";
  return `Moyenne ${annees[0]}–${annees[annees.length - 1]}`;
}

function GraphiquePluie({ tendance }: { tendance: Tendance }) {
  const jeux: ChartData<"bar"> = {
    labels: tendance.labels,
    datasets: [
      {
        label: `Pluie ${tendance.annee_courante} (mm/mois)`,
        data: tendance.pluie_courante_mm,
        backgroundColor: "rgba(25, 118, 210, 0.75)",
        borderColor: "rgba(13, 71, 161, 1)",
        borderWidth: 1,
      },
      {
        label: `${libelleReference(tendance.annees_reference)} (mm/mois)`,
        data: tendance.pluie_moyenne_reference_mm,
        backgroundColor: "rgba(120, 120, 120, 0.45)",
        borderColor: "rgba(80, 80, 80, 1)",
        borderWidth: 1,
      },
    ],
  };
  return (
    <div className="graphique">
      <Bar data={jeux} options={OPTIONS_PLUIE} />
    </div>
  );
}

function GraphiqueTemperature({ tendance }: { tendance: Tendance }) {
  const jeux: ChartData<"line"> = {
    labels: tendance.labels,
    datasets: [
      {
        label: `Tmax ${tendance.annee_courante} (°C)`,
        data: tendance.temp_courante_c,
        borderColor: "rgba(198, 40, 40, 1)",
        backgroundColor: "rgba(198, 40, 40, 0.25)",
        fill: false,
        tension: 0.3,
        spanGaps: true,
      },
      {
        label: `${libelleReference(tendance.annees_reference)} (°C)`,
        data: tendance.temp_moyenne_reference_c,
        borderColor: "rgba(90, 90, 90, 1)",
        borderDash: [6, 4],
        fill: false,
        tension: 0.3,
        spanGaps: true,
      },
    ],
  };
  return (
    <div className="graphique">
      <Line data={jeux} options={OPTIONS_TEMPERATURE} />
    </div>
  );
}

export default function Tendances() {
  const [donnees, setDonnees] = useState<ReponseTendances | null>(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    const controleur = new AbortController();
    setChargement(true);
    getTendances(ZONE, ANNEES_REFERENCE, controleur.signal)
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
    return () => controleur.abort();
  }, []);

  const tendance = donnees?.tendance;

  return (
    <div className="page">
      <h2>Tendances climatiques</h2>
      <p className="page-note">
        Zone de {ZONE} · API {urlApi()} ·{" "}
        {donnees?.derniere_donnee
          ? `dernière donnée au ${donnees.derniere_donnee}`
          : "dates inconnues"}
        .
      </p>

      {chargement && <p role="status">Chargement des tendances…</p>}

      {erreur && (
        <p className="page-erreur" role="alert">
          {erreur}
        </p>
      )}

      {!chargement && !erreur && donnees && !donnees.disponible && (
        <p className="page-erreur" role="alert">
          {donnees.message ?? "Aucune donnée disponible pour cette zone."}
        </p>
      )}

      {tendance && (
        <>
          <p className="page-source">
            Source : {donnees?.source}. Comparaison avec{" "}
            {tendance.annees_reference.length} année(s) de référence
            {tendance.annees_reference.length > 0
              ? ` (${tendance.annees_reference.join(", ")})`
              : ""}
            . Unités : mm/mois et °C.
          </p>
          <GraphiquePluie tendance={tendance} />
          <GraphiqueTemperature tendance={tendance} />
        </>
      )}

      <p className="page-avertissement">
        Données de maille NASA POWER (≈ 0,5°), pas d'une parcelle. À valider avec
        un agronome.
      </p>
    </div>
  );
}
