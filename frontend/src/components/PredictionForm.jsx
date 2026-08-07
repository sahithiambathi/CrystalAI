import { useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { validateMaterialId } from "../lib/format";

export default function PredictionForm({
  examples,
  suggestions,
  materialsProjectEnabled,
  fileName,
  busy,
  onMaterialSubmit,
  onUploadSubmit,
  onMaterialChange,
  onReset,
}) {
  const [materialId, setMaterialId] = useState("mp-1001");
  const [materialError, setMaterialError] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const exampleText = useMemo(() => examples.join(", "), [examples]);

  function submitMaterial(event) {
    event.preventDefault();

    if (!validateMaterialId(materialId)) {
      setMaterialError("Use the Material Project format `mp-1234`.");
      return;
    }

    setMaterialError("");
    onMaterialSubmit(materialId.trim().toLowerCase());
  }

  function handleFileSelection(file) {
    if (!file) {
      return;
    }
    onUploadSubmit(file);
  }

  return (
    <section className="panel input-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Input</p>
          <h2>Predict from a Material ID or CIF upload</h2>
        </div>
        <button className="ghost-button" type="button" onClick={onReset}>
          Reset
        </button>
      </div>

      <form className="material-form" onSubmit={submitMaterial}>
        <label htmlFor="material-id">Material Project ID</label>
        <div className="input-row">
          <input
            id="material-id"
            type="text"
            value={materialId}
            onChange={(event) => {
              const nextValue = event.target.value;
              setMaterialId(nextValue);
              onMaterialChange(nextValue);
            }}
            placeholder="Enter Material Project ID (e.g., mp-1001)"
            autoComplete="off"
          />
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Predicting..." : "Predict"}
          </button>
        </div>
        <p className="helper-text">Try a sample ID: {exampleText}</p>
        <div className="material-search-meta">
          <p className="helper-text">
            Search suggestions come from the local CIF dataset.
            {materialsProjectEnabled
              ? " Live Materials Project fallback is enabled for IDs that are not stored locally."
              : " Add an `MP_API_KEY` on the backend to fetch IDs online when they are missing locally."}
          </p>
          {suggestions.length ? (
            <div className="suggestion-list" role="listbox" aria-label="Available material ids">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  className="suggestion-chip"
                  type="button"
                  onClick={() => {
                    setMaterialId(suggestion);
                    setMaterialError("");
                    onMaterialChange(suggestion);
                    onMaterialSubmit(suggestion);
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        {materialError ? <p className="error-text">{materialError}</p> : null}
      </form>

      <div className="divider">
        <span>or</span>
      </div>

      <motion.div
        className={`dropzone ${dragActive ? "active" : ""}`}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          event.preventDefault();
          setDragActive(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          handleFileSelection(event.dataTransfer.files?.[0]);
        }}
        whileHover={{ y: -2 }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".cif"
          hidden
          onChange={(event) => handleFileSelection(event.target.files?.[0])}
        />
        <p className="dropzone-title">Drop a `.cif` file here</p>
        <p className="helper-text">or choose a local crystal structure file to parse and visualize.</p>
        <button
          className="secondary-button"
          type="button"
          disabled={busy}
          onClick={() => fileInputRef.current?.click()}
        >
          Choose CIF
        </button>
        <p className="helper-text">{fileName || "No file selected yet"}</p>
      </motion.div>
    </section>
  );
}
