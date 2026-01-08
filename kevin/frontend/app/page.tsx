"use client";

import { useEffect, useMemo, useState } from "react";
import { Card } from "./components/Card";
import { Field } from "./components/Field";
import { Button } from "./components/Button";
import { LogConsole } from "./components/LogConsole";
import { runPipeline } from "./api";

const LS = {
  openai: "kevin:key:openai",
  anthropic: "kevin:key:anthropic",
  gemini: "kevin:key:gemini",
  models: "kevin:models",
  paths: "kevin:paths"
};

export default function Page() {
  const [openai, setOpenai] = useState("");
  const [anthropic, setAnthropic] = useState("");
  const [gemini, setGemini] = useState("");

  const [primaryModel, setPrimaryModel] = useState("claude-opus-4-5-20251101");
  const [auditorModel, setAuditorModel] = useState("gpt-5.2-thinking");
  const [gapModel, setGapModel] = useState("gemini-3-pro");

  const [inputDir, setInputDir] = useState("");
  const [outputDir, setOutputDir] = useState("");

  const [running, setRunning] = useState(false);
  const [log, setLog] = useState("");
  const [logFile, setLogFile] = useState<string | null>(null);
  const [runSuccess, setRunSuccess] = useState<boolean | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    setOpenai(localStorage.getItem(LS.openai) || "");
    setAnthropic(localStorage.getItem(LS.anthropic) || "");
    setGemini(localStorage.getItem(LS.gemini) || "");

    const m = localStorage.getItem(LS.models);
    if (m) {
      try {
        const j = JSON.parse(m);
        setPrimaryModel(j.primary || "claude-opus-4-5-20251101");
        setAuditorModel(j.auditor || "gpt-5.2-thinking");
        setGapModel(j.gap || "gemini-3-pro");
      } catch {}
    }
    const p = localStorage.getItem(LS.paths);
    if (p) {
      try {
        const j = JSON.parse(p);
        setInputDir(j.inputDir || "");
        setOutputDir(j.outputDir || "");
      } catch {}
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(LS.openai, openai);
    localStorage.setItem(LS.anthropic, anthropic);
    localStorage.setItem(LS.gemini, gemini);
  }, [openai, anthropic, gemini]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(LS.models, JSON.stringify({
      primary: primaryModel,
      auditor: auditorModel,
      gap: gapModel
    }));
  }, [primaryModel, auditorModel, gapModel]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(LS.paths, JSON.stringify({ inputDir, outputDir }));
  }, [inputDir, outputDir]);

  async function onRun() {
    setRunning(true);
    setLogFile(null);
    setRunSuccess(null);
    setLog("Starting pipeline...\n");
    try {
      const payload = {
        input_dir: inputDir,
        output_dir: outputDir,
        models: {
          primary: primaryModel,
          auditor: auditorModel,
          gapHunter: gapModel
        },
        keys: { openai, anthropic, gemini },
        options: { max_gap_rounds: 2 }
      };
      setLog((prev) => prev + "Sending request to backend...\n");
      const res = await runPipeline(payload);

      // Extract log file path
      if (res.log_file) {
        setLogFile(res.log_file);
      }

      // Track success status
      setRunSuccess(res.ok === true);

      // Format output
      const docsProcessed = res.run?.documents_processed?.length || 0;
      const errorsCount = res.run?.errors?.length || 0;

      let summary = "\n--- Pipeline Complete ---\n";
      summary += `Status: ${res.ok ? 'SUCCESS' : 'FAILED'}\n`;
      summary += `Documents Processed: ${docsProcessed}\n`;
      summary += `Errors: ${errorsCount}\n`;

      if (res.log_file) {
        summary += `\nLog File: ${res.log_file}\n`;
      }

      summary += "\n--- Full Response ---\n";
      summary += JSON.stringify(res, null, 2);

      setLog((prev) => prev + summary);
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      setLog((prev) => prev + "\nERROR: " + errorMessage);
      setRunSuccess(false);
    } finally {
      setRunning(false);
    }
  }

  const canRun = useMemo(() => {
    return !!inputDir && !!outputDir && !!anthropic && !!primaryModel;
  }, [inputDir, outputDir, anthropic, primaryModel]);

  return (
    <main className="max-w-7xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/70 mb-3">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_20px_rgba(16,185,129,.6)]" />
            Multi-Model AI Pipeline
          </div>
          <h1 className="text-4xl font-bold tracking-tight">Kevin</h1>
          <p className="mt-2 text-white/60 max-w-2xl">
            Born-digital PDFs to audited chemistry dataset. Extracts molecules, experiments, and results
            using Claude Opus 4.5, GPT-5.2 audit verification, and Gemini gap analysis.
          </p>
        </div>
        <Button onClick={onRun} disabled={!canRun || running} variant="success">
          {running ? "Running..." : "Run Pipeline"}
        </Button>
      </div>

      {/* Main Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left column - Keys & Folders */}
        <div className="lg:col-span-2 space-y-6">
          <Card title="API Keys (stored in browser only)">
            <div className="grid sm:grid-cols-3 gap-4">
              <Field
                label="Anthropic Key (required)"
                value={anthropic}
                onChange={setAnthropic}
                placeholder="sk-ant-..."
                type="password"
              />
              <Field
                label="OpenAI Key (for audit)"
                value={openai}
                onChange={setOpenai}
                placeholder="sk-..."
                type="password"
              />
              <Field
                label="Gemini Key (for gaps)"
                value={gemini}
                onChange={setGemini}
                placeholder="AIza..."
                type="password"
              />
            </div>
            <p className="mt-4 text-xs text-white/50">
              Keys are stored in localStorage and sent directly to each API. Never stored on any server.
            </p>
          </Card>

          <Card title="Folders (paste full Windows/Mac paths)">
            <div className="grid sm:grid-cols-2 gap-4">
              <Field
                label="Input folder (PDFs)"
                value={inputDir}
                onChange={setInputDir}
                placeholder="C:\data\pdfs"
              />
              <Field
                label="Output folder (dataset)"
                value={outputDir}
                onChange={setOutputDir}
                placeholder="C:\data\kevin_out"
              />
            </div>
            <p className="mt-4 text-xs text-white/50">
              Output contains: dataset.db (SQLite), bundles/ (per-PDF extractions), exports/ (JSONL files), logs/
            </p>
          </Card>
        </div>

        {/* Right column - Models */}
        <div className="space-y-6">
          <Card title="Model Configuration">
            <div className="space-y-4">
              <Field
                label="Primary (Chemist Extractor)"
                value={primaryModel}
                onChange={setPrimaryModel}
              />
              <Field
                label="Auditor (Citation Verifier)"
                value={auditorModel}
                onChange={setAuditorModel}
              />
              <Field
                label="Gap Hunter (Coverage Scanner)"
                value={gapModel}
                onChange={setGapModel}
              />
            </div>
            <div className="mt-4 pt-4 border-t border-white/10">
              <div className="text-xs text-white/50 space-y-1">
                <p><strong>Pipeline:</strong> Opus extracts → GPT-5.2 audits → Auto-repair → Gemini finds gaps → Targeted extraction → Re-audit</p>
              </div>
            </div>
          </Card>

          <Card title="Status">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${canRun ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                <span className="text-sm">
                  {canRun ? 'Ready to run' : 'Configure input/output folders and Anthropic key'}
                </span>
              </div>
              {running && (
                <div className="flex items-center gap-2 text-blue-400">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span className="text-sm">Pipeline running...</span>
                </div>
              )}
              {runSuccess !== null && !running && (
                <div className={`flex items-center gap-2 ${runSuccess ? 'text-emerald-400' : 'text-red-400'}`}>
                  <span className={`h-2 w-2 rounded-full ${runSuccess ? 'bg-emerald-400' : 'bg-red-400'}`} />
                  <span className="text-sm">
                    {runSuccess ? 'Pipeline completed successfully' : 'Pipeline completed with errors'}
                  </span>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Log File Info */}
      {logFile && (
        <Card title="Pipeline Log">
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-1">
                <svg className="h-5 w-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white">Detailed Log File Created</p>
                <p className="text-xs text-white/60 mt-1 break-all font-mono bg-black/30 rounded px-2 py-1">
                  {logFile}
                </p>
                <p className="text-xs text-white/50 mt-2">
                  Open this Markdown file in any text editor or Markdown viewer to see the complete pipeline report with:
                </p>
                <ul className="text-xs text-white/50 mt-1 ml-4 list-disc space-y-0.5">
                  <li>Stage-by-stage timing and statistics</li>
                  <li>API call logs with token usage</li>
                  <li>Errors and warnings summary</li>
                  <li>Extraction results summary</li>
                  <li>Recommendations for improvement</li>
                </ul>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Console */}
      <Card title="Console Output">
        <LogConsole text={log} />
      </Card>

      {/* Footer */}
      <div className="text-center text-xs text-white/40 pt-4">
        Kevin v1.0 — Built for chemistry dataset extraction from scientific literature
      </div>
    </main>
  );
}
