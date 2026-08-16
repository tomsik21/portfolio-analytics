import { useEffect, useState } from "react";
import { getAttribution, AttributionResponse } from "../api/client";

interface Props {
  portfolioId: string;
  start: string;
  end: string;
}

function pct(n: number): string {
  return `${(n * 100).toFixed(2)}%`;
}

export default function AttributionCard({ portfolioId, start, end }: Props) {
  const [data, setData] = useState<AttributionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    setData(null);
    getAttribution(portfolioId, start, end)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [portfolioId, start, end]);

  return (
    <div className="card">
      <h2>Brinson-Fachler Attribution</h2>
      {error && <div className="status-banner error">{error}</div>}
      {!error && !data && (
        <div className="status-banner loading">Loading…</div>
      )}
      {data && (
        <>
          <div className="metric-row" style={{ marginBottom: 20 }}>
            <div className="metric">
              <div
                className={`value ${data.active_return >= 0 ? "positive" : "negative"}`}
                data-testid="attribution-active-return"
              >
                {pct(data.active_return)}
              </div>
              <div className="label">Active return</div>
            </div>
            <div className="metric">
              <div className="value">{pct(data.portfolio_total_return)}</div>
              <div className="label">Portfolio return</div>
            </div>
            <div className="metric">
              <div className="value">{pct(data.benchmark_total_return)}</div>
              <div className="label">Benchmark return</div>
            </div>
          </div>
          <table data-testid="attribution-table">
            <thead>
              <tr>
                <th>Sector</th>
                <th>Allocation</th>
                <th>Selection</th>
                <th>Interaction</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {data.sectors.map((s) => (
                <tr key={s.sector} data-testid={`attribution-row-${s.sector}`}>
                  <td>{s.sector}</td>
                  <td>{pct(s.allocation_effect)}</td>
                  <td>{pct(s.selection_effect)}</td>
                  <td>{pct(s.interaction_effect)}</td>
                  <td>{pct(s.total_effect)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p
            style={{ fontSize: 12, color: "#888", marginTop: 12, marginBottom: 0 }}
            data-testid="attribution-reconciliation-delta"
          >
            Reconciliation delta: {data.reconciliation_delta.toExponential(2)} (should be ~0 —
            confirms allocation + selection + interaction sum exactly to active return)
          </p>
        </>
      )}
    </div>
  );
}
