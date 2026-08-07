import { useEffect, useState } from "react";
import { LazyMotion, domAnimation, m } from "framer-motion";
import LoadingSkeleton from "./components/LoadingSkeleton";
import PredictionForm from "./components/PredictionForm";
import ResultsPanel from "./components/ResultsPanel";
import ThemeToggle from "./components/ThemeToggle";
import { fetchExamples, predictFromMaterialId, predictFromUpload, searchMaterialIds } from "./lib/api";

function normalizePrediction(payload) {
  return {
    sourceType: payload.source_type,
    sourceLabel: payload.source_label,
    name: payload.name,
    formula: payload.formula,
    summary: payload.summary,
    insights: payload.insights,
    applications: payload.applications,
    metrics: {
      bandGapEv: payload.metrics.band_gap_ev,
      formationEnergyEvAtom: payload.metrics.formation_energy_ev_atom,
      confidence: payload.metrics.confidence,
    },
    crystal: {
      ...payload.crystal,
      atomCount: payload.crystal.atom_count,
    },
  };
}

export default function App() {
  const [theme, setTheme] = useState("light");
  const [examples, setExamples] = useState(["mp-1001"]);
  const [suggestions, setSuggestions] = useState(["mp-1001"]);
  const [materialsProjectEnabled, setMaterialsProjectEnabled] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchExamples()
      .then((payload) => setExamples(payload.material_ids))
      .catch(() => {
        // Keep the default sample if the API is not ready yet.
      });
  }, []);

  useEffect(() => {
    searchMaterialIds("")
      .then((payload) => {
        setSuggestions(payload.material_ids);
        setMaterialsProjectEnabled(payload.materials_project_enabled);
      })
      .catch(() => {
        // Keep defaults when the search endpoint is not reachable.
      });
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  async function runAction(action) {
    setBusy(true);
    setError("");

    try {
      const result = await action();
      setPrediction(normalizePrediction(result));
    } catch (nextError) {
      setError(nextError.message);
      setPrediction(null);
    } finally {
      setBusy(false);
    }
  }

  function resetAll() {
    setPrediction(null);
    setError("");
    setFileName("");
  }

  async function handleMaterialInputChange(value) {
    try {
      const payload = await searchMaterialIds(value);
      setSuggestions(payload.material_ids);
      setMaterialsProjectEnabled(payload.materials_project_enabled);
    } catch {
      // Keep the last successful suggestions visible.
    }
  }

  return (
    <LazyMotion features={domAnimation}>
      <div className="app-shell">
        <div className="ambient ambient-one" />
        <div className="ambient ambient-two" />

        <header className="hero">
          <nav className="topbar">
            <div className="brand">
              <span className="brand-mark">C</span>
              <div>
                <strong>CrystalAI</strong>
                <p>Crystal based multimodal material property prediction</p>
              </div>
            </div>
            <ThemeToggle
              theme={theme}
              onToggle={() => setTheme((current) => (current === "light" ? "dark" : "light"))}
            />
          </nav>

          <m.div
            className="hero-copy"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
          >
            <p className="eyebrow">Modern Materials UX</p>
            <h1>Predict material properties from crystal structure with an interactive 3D workflow.</h1>
            <p className="hero-description">
              Search by Material Project ID or upload a CIF file to estimate band gap, formation
              energy, and application fit while exploring the parsed crystal in real time.
            </p>
          </m.div>
        </header>

        <main className="main-grid">
          <PredictionForm
            examples={examples}
            suggestions={suggestions}
            materialsProjectEnabled={materialsProjectEnabled}
            fileName={fileName}
            busy={busy}
            onMaterialSubmit={(materialId) => runAction(() => predictFromMaterialId(materialId))}
            onMaterialChange={handleMaterialInputChange}
            onUploadSubmit={(file) => {
              setFileName(file.name);
              runAction(() => predictFromUpload(file));
            }}
            onReset={resetAll}
          />

          {busy ? <LoadingSkeleton /> : <ResultsPanel prediction={prediction} />}
        </main>

        {error ? (
          <m.div className="toast-error" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            {error}
          </m.div>
        ) : null}
      </div>
    </LazyMotion>
  );
}
