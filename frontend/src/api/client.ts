// Thin typed wrapper around fetch(). Requests go to /api/... which
// vite.config.ts proxies to the FastAPI backend on :8000 — see the
// comment there for why.

export interface HealthResponse {
  status: string;
}

export interface TWRResponse {
  portfolio_id: string;
  period_start: string;
  period_end: string;
  twr: number;
  num_subperiods: number;
}

export interface SectorAttribution {
  sector: string;
  allocation_effect: number;
  selection_effect: number;
  interaction_effect: number;
  total_effect: number;
}

export interface AttributionResponse {
  portfolio_id: string;
  period_start: string;
  period_end: string;
  portfolio_total_return: number;
  benchmark_total_return: number;
  active_return: number;
  reconciliation_delta: number;
  sectors: SectorAttribution[];
}

export interface PnLResponse {
  portfolio_id: string;
  security_id: string;
  as_of: string;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  open_quantity: number;
  current_price: number;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export function getHealth(): Promise<HealthResponse> {
  return getJSON<HealthResponse>("/health");
}

export function getTWR(
  portfolioId: string,
  start: string,
  end: string
): Promise<TWRResponse> {
  return getJSON<TWRResponse>(
    `/portfolios/${portfolioId}/performance/twr?start=${start}&end=${end}`
  );
}

export function getAttribution(
  portfolioId: string,
  start: string,
  end: string
): Promise<AttributionResponse> {
  return getJSON<AttributionResponse>(
    `/portfolios/${portfolioId}/attribution/brinson?start=${start}&end=${end}`
  );
}

export function getPnL(
  portfolioId: string,
  securityId: string,
  asOf: string
): Promise<PnLResponse> {
  return getJSON<PnLResponse>(
    `/portfolios/${portfolioId}/pnl?security_id=${securityId}&as_of=${asOf}`
  );
}
