export async function runPipeline(payload: {
  input_dir: string;
  output_dir: string;
  models: { primary: string; auditor: string; gapHunter: string };
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
