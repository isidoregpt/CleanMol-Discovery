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
      setLog((prev) => prev + "\nPipeline complete!\n\n" + JSON.stringify(res, null, 2));
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      setLog((prev) => prev + "\nERROR: " + errorMessage);
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
            </div>
          </Card>
        </div>
      </div>

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
