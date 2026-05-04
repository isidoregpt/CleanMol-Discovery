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
};

export async function getDefaults(): Promise<DefaultsResponse> {
  const r = await fetch("http://localhost:8787/api/defaults");
  const j = await r.json();
  if (!r.ok) throw new Error(j?.detail || "Defaults request failed");
  return j;
}

export async function runPipeline(payload: {
  input_dir: string;
  output_dir: string;
  models: ModelBundle;
  keys: { openai: string; anthropic: string; gemini: string };
  options?: { max_gap_rounds?: number };
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
