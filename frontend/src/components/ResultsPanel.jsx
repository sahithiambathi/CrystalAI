import { motion } from "framer-motion";
import CrystalViewer from "./CrystalViewer";
import InfoTip from "./InfoTip";
import { downloadPredictionPdf, formatMetric } from "../lib/format";

function MetricCard({ label, value, helper }) {
  return (
    <motion.article className="metric-card" whileHover={{ y: -6 }}>
      <p className="metric-label">
        {label}
        {helper ? <InfoTip label={label} text={helper} /> : null}
      </p>
      <h3>{value}</h3>
    </motion.article>
  );
}

export default function ResultsPanel({ prediction }) {
  if (!prediction) {
    return (
      <section className="panel results-panel empty-state">
        <p className="eyebrow">Output</p>
        <h2>Interactive predictions appear here</h2>
        <p>
          Submit a Material Project ID or upload a CIF file to render the crystal structure and
          estimate material properties.
        </p>
      </section>
    );
  }

  return (
    <section className="panel results-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Output</p>
          <h2>
            {prediction.formula}{" "}
            {prediction.name ? (
              <span style={{ fontSize: "0.75em", color: "var(--muted)", fontWeight: "normal" }}>
                ({prediction.name})
              </span>
            ) : null}{" "}
            report
          </h2>
          <p className="helper-text">Source: {prediction.sourceLabel}</p>
        </div>
        <button className="secondary-button" type="button" onClick={() => downloadPredictionPdf(prediction)}>
          Download PDF
        </button>
      </div>

      <div className="results-grid">
        <MetricCard
          label="Band Gap"
          value={formatMetric(prediction.metrics.bandGapEv, "eV")}
          helper="Band gap measures the energy needed to move electrons into a conducting state."
        />
        <MetricCard
          label="Formation Energy"
          value={formatMetric(prediction.metrics.formationEnergyEvAtom, "eV/atom")}
          helper="Formation energy estimates how favorable it is for the crystal to form."
        />
        <MetricCard
          label="Confidence"
          value={`${Math.round(prediction.metrics.confidence * 100)}%`}
        />
      </div>

      <div className="content-grid">
        <div className="content-card">
          <h3>Insights</h3>
          <p>{prediction.summary}</p>
          <ul>
            {prediction.insights.map((insight) => (
              <li key={insight}>{insight}</li>
            ))}
          </ul>
        </div>

        <div className="content-card">
          <h3>Applications</h3>
          <ul>
            {prediction.applications.map((application) => (
              <li key={application}>{application}</li>
            ))}
          </ul>
          <div className="lattice-stats">
            <span>{prediction.crystal.atomCount} atoms</span>
            <span>{prediction.crystal.bonds.length} bonds</span>
            <span>{prediction.crystal.lattice.volume.toFixed(2)} A^3</span>
          </div>
        </div>
      </div>

      <div className="viewer-card">
        <div className="viewer-header">
          <div>
            <h3>Crystal structure</h3>
            <p>Rotate, zoom, and pan the structure. The viewer auto-centers the parsed unit cell.</p>
          </div>
        </div>
        <CrystalViewer crystal={prediction.crystal} />
      </div>
    </section>
  );
}
