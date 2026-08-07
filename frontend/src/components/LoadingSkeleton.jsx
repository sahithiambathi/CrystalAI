export default function LoadingSkeleton() {
  return (
    <section className="panel results-panel">
      <p className="eyebrow">Output</p>
      <h2>Analyzing crystal structure</h2>
      <div className="results-grid">
        {[0, 1, 2].map((item) => (
          <div className="skeleton-card" key={item}>
            <span className="skeleton skeleton-title" />
            <span className="skeleton skeleton-line" />
            <span className="skeleton skeleton-line short" />
          </div>
        ))}
      </div>
    </section>
  );
}
