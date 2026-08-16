import { useEffect, useState } from "react";
import { getTWR, TWRResponse } from "../api/client";

interface Props {
  portfolioId: string;
  start: string;
  end: string;
}

export default function TwrCard({ portfolioId, start, end }: Props) {
  const [data, setData] = useState<TWRResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    setData(null);
    getTWR(portfolioId, start, end)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [portfolioId, start, end]);

  return (
    <div className="card">
      <h2>Time-Weighted Return</h2>
      {error && <div className="status-banner error">{error}</div>}
      {!error && !data && (
        <div className="status-banner loading">Loading…</div>
      )}
      {data && (
        <div className="metric-row">
          <div className="metric">
            <div
              className={`value ${data.twr >= 0 ? "positive" : "negative"}`}
              data-testid="twr-value"
            >
              {(data.twr * 100).toFixed(2)}%
            </div>
            <div className="label">TWR ({data.period_start} → {data.period_end})</div>
          </div>
          <div className="metric">
            <div className="value" data-testid="twr-subperiods">{data.num_subperiods}</div>
            <div className="label">Sub-periods linked</div>
          </div>
        </div>
      )}
    </div>
  );
}
