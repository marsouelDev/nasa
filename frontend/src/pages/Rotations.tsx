import { useRef } from "react";

export default function Rotations() {
  const scenariosRef = useRef([
    {
      id: "S0",
      nom: "Rotation actuelle",
      score: 4.73,
      why: "Rotation de référence.",
    },
    {
      id: "S1",
      nom: "Maïs puis légumineuse",
      score: 6.4,
      why: "Maïs + légumineuse.",
    },
    {
      id: "S2",
      nom: "Maïs plus culture de couverture",
      score: 5.73,
      why: "Maïs + culture couverture.",
    },
  ]);

  return (
    <div>
      <h2>Comparateur de rotations</h2>
      {scenariosRef.current.map((s) => (
        <div key={s.id} style={{ marginBottom: "15px", padding: "8px", border: "1px solid #ddd" }}>
          <strong>{s.nom} : </strong> {s.score} - {s.why}
        </div>
      ))}
    </div>
  );
}