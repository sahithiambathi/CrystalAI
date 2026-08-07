export default function InfoTip({ label, text }) {
  return (
    <span className="info-tip" tabIndex="0" aria-label={`${label}: ${text}`}>
      i
      <span className="info-tip__bubble">{text}</span>
    </span>
  );
}
