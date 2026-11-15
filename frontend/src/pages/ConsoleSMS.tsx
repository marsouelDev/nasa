import { useState } from "react";

export default function ConsoleSMS() {
  const [message, setMessage] = useState<string>("");
  const [numero, setNumero] = useState<string>("");

  const envoyer = () => {
    if (!numero || !message) return;
    const sms = `AgroSentry : ${message} (confiance élevée). Valider avec un agronome.`;
    setMessage(sms);
    setTimeout(() => setMessage(""), 3000);
  };

  return (
    <div style={{ padding: "20px" }}>
      <h2>Simulateur SMS / USSD</h2>
      <div style={{ marginBottom: "15px" }}>
        <label>Numéro : </label>
        <input
          type="tel"
          value={numero}
          onChange={(e) => setNumero(e.target.value)}
          placeholder="+237XXXXXXXX"
        />
      </div>
      <div style={{ marginBottom: "15px" }}>
        <label>Message : </label>
        <textarea
          rows={3}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ex: Risque de sécheresse détecté"
        ></textarea>
        <div style={{ fontSize: "0.8em", color: "#666" }}>
          max 160 caractères (simulé)
        </div>
      </div>
      <button onClick={envoyer} style={{ marginTop: "10px" }}>Envoyer SMS</button>
      {message && (
        <div style={{ marginTop: "10px", padding: "8px", background: "#e8f4fd", borderRadius: "4px" }}>
          <strong>SMS simulé :</strong> {message}
        </div>
      )}
    </div>
  );
}