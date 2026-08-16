import { useState } from "react";
import { getAttributionInsight } from "../api/client";

interface Props {
  portfolioId: string;
  start: string;
  end: string;
}

export default function AgentInsightPanel({ portfolioId, start, end }: Props) {
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    setSummary(null);
    try {
      const res = await getAttributionInsight(portfolioId, start, end);
      setSummary(res.summary);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card agent-panel">
      <h2>AI Insight Agent</h2>
      <p style={{ fontSize: 13, color: "#666", marginTop: -8 }}>
        Narrates the attribution numbers above in plain English. The agent only
        explains numbers the calculation engine already computed — it never
        does the math itself.
      </p>
      <button onClick={handleGenerate} disabled={loading} data-testid="agent-generate-button">
        {loading ? "Generating…" : "Generate insight"}
      </button>
      {error && (
        <div className="status-banner error" style={{ marginTop: 14 }} data-testid="agent-error">
          {error}
          {error.includes("ANTHROPIC_API_KEY") && (
            <>
              {" "}
              (This is expected if you haven't set an API key — see the README's
              AI Insight Agent section.)
            </>
          )}
        </div>
      )}
      {summary && <div className="agent-response" data-testid="agent-summary">{summary}</div>}
    </div>
  );
}
