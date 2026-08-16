import { useEffect, useState } from "react";
import { getHealth } from "./api/client";
import TwrCard from "./components/TwrCard";
import AttributionCard from "./components/AttributionCard";
import PnlCard from "./components/PnlCard";
import AgentInsightPanel from "./components/AgentInsightPanel";

// Seed data (app/seed_data.py) only covers this one portfolio/security —
// hardcoding these as sensible defaults rather than building a full
// portfolio picker, since that's not what this step is teaching.
const DEFAULT_PORTFOLIO = "PORT1";
const DEFAULT_SECURITY = "AAPL_DEMO";

export default function App() {
  const [backendStatus, setBackendStatus] = useState<
    "checking" | "ok" | "error"
  >("checking");

  const [portfolioId, setPortfolioId] = useState(DEFAULT_PORTFOLIO);
  const [securityId, setSecurityId] = useState(DEFAULT_SECURITY);
  const [twrStart, setTwrStart] = useState("2026-01-01");
  const [twrEnd, setTwrEnd] = useState("2026-01-03");
  const [attrStart, setAttrStart] = useState("2026-01-01");
  const [attrEnd, setAttrEnd] = useState("2026-01-31");
  const [asOf, setAsOf] = useState("2026-01-31");

  useEffect(() => {
    getHealth()
      .then(() => setBackendStatus("ok"))
      .catch(() => setBackendStatus("error"));
  }, []);

  return (
    <div className="app-shell">
      <div className="app-header">
        <h1>Performance &amp; Analytics Platform</h1>
        <p>TWR · Brinson Attribution · P&amp;L</p>
      </div>

      {backendStatus === "error" && (
        <div className="status-banner error">
          Can't reach the backend API. Is <code>uvicorn app.main:app --reload</code>{" "}
          running on port 8000?
        </div>
      )}

      <div className="card">
        <h2>Filters</h2>
        <div className="metric-row">
          <label>
            Portfolio ID
            <br />
            <input
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              data-testid="input-portfolio-id"
            />
          </label>
          <label>
            Security ID (for P&amp;L)
            <br />
            <input
              value={securityId}
              onChange={(e) => setSecurityId(e.target.value)}
              data-testid="input-security-id"
            />
          </label>
        </div>
      </div>

      {backendStatus === "ok" && (
        <>
          <div className="card">
            <h2>TWR period</h2>
            <div className="metric-row">
              <label>
                Start
                <br />
                <input
                  type="date"
                  value={twrStart}
                  onChange={(e) => setTwrStart(e.target.value)}
                  data-testid="input-twr-start"
                />
              </label>
              <label>
                End
                <br />
                <input
                  type="date"
                  value={twrEnd}
                  onChange={(e) => setTwrEnd(e.target.value)}
                  data-testid="input-twr-end"
                />
              </label>
            </div>
          </div>
          <TwrCard portfolioId={portfolioId} start={twrStart} end={twrEnd} />

          <div className="card">
            <h2>Attribution period</h2>
            <div className="metric-row">
              <label>
                Start
                <br />
                <input type="date" value={attrStart} onChange={(e) => setAttrStart(e.target.value)} />
              </label>
              <label>
                End
                <br />
                <input type="date" value={attrEnd} onChange={(e) => setAttrEnd(e.target.value)} />
              </label>
            </div>
          </div>
          <AttributionCard portfolioId={portfolioId} start={attrStart} end={attrEnd} />
          <AgentInsightPanel portfolioId={portfolioId} start={attrStart} end={attrEnd} />

          <div className="card">
            <h2>P&amp;L as-of date</h2>
            <label>
              As of
              <br />
              <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
            </label>
          </div>
          <PnlCard portfolioId={portfolioId} securityId={securityId} asOf={asOf} />
        </>
      )}
    </div>
  );
}
