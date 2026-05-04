export type ModelBundle = {
  primary: string;
  auditor: string;
  gapHunter: string;
  figure?: string;
};

export type DefaultsResponse = {
  models: ModelBundle;
  legacy_model_aliases: Record<string, string>;
  model_defaults_last_verified?: string;
  model_default_source_urls?: Record<string, string>;
  provider_model_api_urls?: Record<string, string>;
  model_default_mode?: string;
  resolved_at?: string;
  resolution?: Record<string, {
    provider?: string;
    model?: string;
    status?: string;
    reason?: string;
    source?: string;
    selection?: string;
  }>;
};

export type ProviderKeys = { openai: string; anthropic: string; gemini: string };

export async function getDefaults(): Promise<DefaultsResponse> {
  const r = await fetch("http://localhost:8787/api/defaults");
  const j = await r.json();
  if (!r.ok) throw new Error(j?.detail || "Defaults request failed");
  return j;
}

export async function resolveLatestDefaults(keys: ProviderKeys): Promise<DefaultsResponse> {
  const r = await fetch("http://localhost:8787/api/defaults/resolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keys }),
  });
  const j = await r.json();
  if (!r.ok) throw new Error(j?.detail || "Latest defaults request failed");
  return j;
}

export async function runPipeline(payload: {
  input_dir: string;
  output_dir: string;
  models: ModelBundle;
  keys: ProviderKeys;
  options?: { max_gap_rounds?: number; resolve_latest_models?: boolean };
}) {
  const r = await fetch("http://localhost:8787/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const j = await r.json();
  if (!r.ok) throw new Error(j?.detail || "Request failed");
  return j;
}
