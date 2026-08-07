import { jsPDF } from "jspdf";

export function formatMetric(value, unit, digits = 2) {
  return `${Number(value).toFixed(digits)} ${unit}`;
}

export function validateMaterialId(value) {
  return /^mp-\d+$/i.test(value.trim());
}

export function downloadPredictionPdf(prediction) {
  const doc = new jsPDF();

  doc.setFontSize(18);
  doc.text("CrystalAI Prediction Report", 20, 20);

  doc.setFontSize(11);
  doc.text(`Source: ${prediction.sourceLabel}`, 20, 35);
  doc.text(`Formula: ${prediction.formula}`, 20, 43);
  doc.text(`Band Gap: ${prediction.metrics.bandGapEv.toFixed(2)} eV`, 20, 51);
  doc.text(
    `Formation Energy: ${prediction.metrics.formationEnergyEvAtom.toFixed(2)} eV/atom`,
    20,
    59,
  );
  doc.text(`Confidence: ${(prediction.metrics.confidence * 100).toFixed(0)}%`, 20, 67);

  const summaryLines = doc.splitTextToSize(prediction.summary, 170);
  doc.text(summaryLines, 20, 83);

  doc.text("Insights", 20, 112);
  prediction.insights.forEach((insight, index) => {
    const lines = doc.splitTextToSize(`- ${insight}`, 170);
    doc.text(lines, 20, 120 + index * 12);
  });

  doc.save(`${prediction.sourceLabel}-prediction.pdf`);
}
