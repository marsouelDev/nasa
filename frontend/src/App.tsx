import Carte from "./components/Carte";
import Tendances from "./pages/Tendances";
import Rotations from "./pages/Rotations";
import ConsoleSMS from "./pages/ConsoleSMS";

export default function App() {
  const pathname = window.location.pathname || "/";
  let Page;
  if (pathname === "/tendances") Page = <Tendances />;
  else if (pathname === "/rotations") Page = <Rotations />;
  else if (pathname === "/sms") Page = <ConsoleSMS />;
  else Page = <Carte />;

  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      <nav
        style={{
          position: "absolute",
          top: 12,
          left: 12,
          display: "flex",
          gap: 12,
          zIndex: 10,
        }}
      >
        <a href="/" style={{ textDecoration: "none", color: "white" }}>Accueil</a>
        <a href="/tendances" style={{ textDecoration: "none", color: "white" }}>Tendances</a>
        <a href="/rotations" style={{ textDecoration: "none", color: "white" }}>Rotations</a>
        <a href="/sms" style={{ textDecoration: "none", color: "white" }}>SMS</a>
      </nav>
      {Page}
    </div>
  );
}