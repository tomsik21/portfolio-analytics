import { useEffect, useState } from "react";
import { getPnL, PnLResponse } from "../api/client";

interface Props {
  portfolioId: string;
  securityId: string;
  asOf: string;
}

function usd(n: number): string {
  const sign = n < 0 ? "-" : "";
  return `${sign}$${Math.abs(n).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export default function PnlCard({ portfolioId, securityId, asOf }: Props) {
  const [data, setData] = useState<PnLResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    setData(null);
    getPnL(portfolioId, securityId, asOf)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [portfolioId, securityId, asOf]);

  return (
    <div className="card">
      <h2>P&amp;L — {securityId} (FIFO)</h2>
      {error && <div className="status-banner error">{error}</div>}
      {!error && !data && (
        <div className="status-banner loading">Loading…</div>
      )}
      {data && (
        <div className="metric-row">
          <div className="metric">
            <div
              className={`value ${data.realized_pnl >= 0 ? "positive" : "negative"}`}
              data-testid="pnl-realized"
            >
              {usd(data.realized_pnl)}
            </div>
            <div className="label">Realized P&amp;L</div>
          </div>
          <div className="metric">
            <div
              className={`value ${data.unrealized_pnl >= 0 ? "positive" : "negative"}`}
              data-testid="pnl-unrealized"
            >
              {usd(data.unrealized_pnl)}
            </div>
            <div className="label">Unrealized P&amp;L</div>
          </div>
          <div className="metric">
            <div className="value" data-testid="pnl-open-quantity">{data.open_quantity}</div>
            <div className="label">Open quantity</div>
          </div>
          <div className="metric">
            <div className="value">{usd(data.current_price)}</div>
            <div className="label">Current price</div>
          </div>
        </div>
      )}
    </div>
  );
}
