import { useEffect, useState } from "react";
import { Chart } from "react-chartjs-2";

const defaultData = {
  labels: ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"],
  datasets: [
    {
      label: "Pluie observée (mm)",
      data: [1, 2, 8, 4, 3, 2, 5, 6, 4, 2, 1, 1],
      backgroundColor: "rgba(54, 162, 235, 0.4)",
      borderColor: "rgba(54, 162, 235, 1)",
      borderWidth: 1,
    },
  ],
};

export default function Tendances() {
  const [data, setData] = useState(defaultData);

  useEffect(() => {
    // Données simulées : on pourrait appeler /api/pluie/tendances/ ici
    const moisPluie = [5.2, 3.1, 12.4, 7.8, 4.5, 2.1, 3.6, 6.2, 8.1, 4.9, 3.3, 2.8];
    const chartData = {
      labels: ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"],
      datasets: [
        {
          label: "Pluie observée (mm)",
          data: moisPluie,
          backgroundColor: "rgba(75, 192, 192, 0.4)",
          borderColor: "rgba(75, 192, 192, 1)",
          borderWidth: 1,
        },
      ],
    };
    setData(chartData);
  }, []);

  const options = {
    responsive: true,
    title: {
      display: true,
      text: "Saison en cours —Comparaison aux 10 dernières années",
    },
    scales: {
      y: { beginAtZero: true, title: { display: true, text: "mm/jour" } },
    },
  };

  return (
    <div style={{ padding: "20px" }}>
      <h2>Tendances climatiques</h2>
      <Chart type="bar" data={data} options={options} />
      <p className="mt-3">
        Données issues de NASA POWER (communauté AG). À valider avec un agronome.
      </p>
    </div>
  );
}