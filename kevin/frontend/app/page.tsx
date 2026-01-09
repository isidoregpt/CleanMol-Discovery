"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
import { ProgressBar } from "./components/ProgressBar";
import { Terminal, TerminalLine } from "./components/Terminal";
import { StageTracker } from "./components/StageTracker";
import { StatCard } from "./components/StatCard";
import { DNALoader } from "./components/DNALoader";

const LS = {
  openai: "kevin:key:openai",
  anthropic: "kevin:key:anthropic",
  gemini: "kevin:key:gemini",
  models: "kevin:models",
  paths: "kevin:paths"
};

const PIPELINE_STAGES = [
  { id: "pdf", name: "PDF Extraction", icon: "📄" },
  { id: "figure", name: "Figure Analysis", icon: "🖼️" },
  { id: "opus", name: "Opus Extraction", icon: "🧬" },
  { id: "audit", name: "GPT-5.2 Audit", icon: "🔍" },
  { id: "repair", name: "Auto-Repair", icon: "🔧" },
  { id: "gap", name: "Gemini Gap Hunt", icon: "🎯" },
  { id: "resolve", name: "Gap Resolution", icon: "✨" },
  { id: "smiles", name: "SMILES Lookup", icon: "🔬" },
  { id: "validate", name: "SMILES Validation", icon: "✓" },
  { id: "export", name: "Export Dataset", icon: "💾" },
];

// Stage weights for weighted progress calculation
const STAGE_WEIGHTS: Record<string, number> = {
  PDF: 8,
  FIGURE: 15,
  OPUS: 22,
  AUDIT: 14,
  REPAIR: 4,
  GAP: 10,
  RESOLVE: 10,
  SMILES: 6,
  VALIDATE: 6,
  EXPORT: 5,
};

const STAGE_ORDER = ["PDF", "FIGURE", "OPUS", "AUDIT", "REPAIR", "GAP", "RESOLVE", "SMILES", "VALIDATE", "EXPORT"];

// Creep function: starts fast, slows down, never reaches cap
function creepProgress(elapsedMs: number, cap = 0.92, speed = 0.0003): number {
  return cap * (1 - Math.exp(-speed * elapsedMs));
}

export default function Page() {
  // API Keys
  const [openai, setOpenai] = useState("");
  const [anthropic, setAnthropic] = useState("");
  const [gemini, setGemini] = useState("");

  // Models
  const [primaryModel, setPrimaryModel] = useState("claude-opus-4-5-20251101");
  const [auditorModel, setAuditorModel] = useState("gpt-5.2-2025-12-11");
  const [gapModel, setGapModel] = useState("gemini-3-pro-preview");

  // Paths
  const [inputDir, setInputDir] = useState("");
  const [outputDir, setOutputDir] = useState("");

  // Pipeline state
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState("");
  const [terminalLines, setTerminalLines] = useState<TerminalLine[]>([]);
  const [stages, setStages] = useState(
    PIPELINE_STAGES.map(s => ({ ...s, status: "pending" as const, detail: "" }))
  );

  // Streaming progress state
  const [docIndex, setDocIndex] = useState(0);
  const [docTotal, setDocTotal] = useState(0);
  const [stageStartTime, setStageStartTime] = useState<number | null>(null);
  const [stageProgress, setStageProgress] = useState<Record<string, number>>({});
  const [lastUpdate, setLastUpdate] = useState(Date.now());

  // Results
  const [stats, setStats] = useState({
    molecules: 0,
    experiments: 0,
    results: 0,
    documents: 0,
  });
  const [completed, setCompleted] = useState(false);
  const [logFile, setLogFile] = useState("");

  // Load saved settings
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

  // Save settings
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

  // Creep animation for progress bar during LLM calls
  useEffect(() => {
    if (!running || !stageStartTime) return;

    const interval = setInterval(() => {
      const elapsed = Date.now() - stageStartTime;
      const creep = creepProgress(elapsed);

      // Calculate weighted progress
      let totalWeight = 0;
      let completedWeight = 0;

      for (const stage of STAGE_ORDER) {
        const weight = STAGE_WEIGHTS[stage] || 0;
        totalWeight += weight;

        if (stageProgress[stage] === 1) {
          completedWeight += weight;
        } else if (stage === currentStage) {
          completedWeight += weight * creep;
        }
      }

      // Factor in document progress
      const docProgressVal = docTotal > 0 ? (docIndex - 1) / docTotal : 0;
      const currentDocProgress = totalWeight > 0 ? completedWeight / totalWeight : 0;
      const overall = docTotal > 0
        ? (docProgressVal + currentDocProgress / docTotal) * 100
        : currentDocProgress * 100;

      setProgress(Math.min(99, overall));
    }, 200);

    return () => clearInterval(interval);
  }, [running, stageStartTime, currentStage, stageProgress, docIndex, docTotal]);

  // Terminal logging
  const addLog = useCallback((text: string, type: TerminalLine["type"] = "info", prefix?: string) => {
    const timestamp = new Date().toLocaleTimeString("en-US", { hour12: false });
    setTerminalLines(prev => [...prev, { timestamp, type, prefix, text }]);
  }, []);

  // Update stage status
  const updateStage = useCallback((stageId: string, status: "pending" | "active" | "completed" | "error", detail?: string) => {
    setStages(prev => prev.map(s =>
      s.id === stageId ? { ...s, status, detail: detail || s.detail } : s
    ));
  }, []);

  // Map backend stage names to frontend stage IDs
  const stageToId: Record<string, string> = {
    PDF: "pdf",
    FIGURE: "figure",
    OPUS: "opus",
    AUDIT: "audit",
    REPAIR: "repair",
    GAP: "gap",
    RESOLVE: "resolve",
    SMILES: "smiles",
    VALIDATE: "validate",
    EXPORT: "export",
  };

  // Run pipeline with streaming SSE updates
  const runPipeline = async () => {
    setRunning(true);
    setCompleted(false);
    setProgress(0);
    setTerminalLines([]);
    setStages(PIPELINE_STAGES.map(s => ({ ...s, status: "pending" as const, detail: "" })));
    setStats({ molecules: 0, experiments: 0, results: 0, documents: 0 });
    setLogFile("");
    setStageProgress({});
    setCurrentStage("");
    setDocIndex(0);
    setDocTotal(0);
    setStageStartTime(null);

    addLog("Initializing Kevin Pipeline v1.0", "system", "SYSTEM");
    addLog(`Input: ${inputDir}`, "dim");
    addLog(`Output: ${outputDir}`, "dim");
    addLog("", "dim");

    let buffer = "";

    try {
      addLog("Connecting to backend server (streaming)...", "info", "NET");

      const response = await fetch("http://localhost:8787/api/run-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input_dir: inputDir,
          output_dir: outputDir,
          models: {
            primary: primaryModel,
            auditor: auditorModel,
            gapHunter: gapModel
          },
          keys: { openai, anthropic, gemini },
          options: { max_gap_rounds: 2 }
        }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response body");

      addLog("Connected! Receiving real-time updates...", "success", "NET");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE events (split on \n\n)
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";  // Keep incomplete event in buffer

        for (const event of events) {
          for (const line of event.split("\n")) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                setLastUpdate(Date.now());

                if (data.type === "progress") {
                  addLog(data.message, "info");
                } else if (data.type === "stage_progress") {
                  setDocIndex(data.doc_index || 0);
                  setDocTotal(data.doc_total || 0);

                  const stageId = stageToId[data.stage] || data.stage.toLowerCase();

                  if (data.event === "start") {
                    setCurrentStage(data.stage);
                    setStageStartTime(Date.now());
                    updateStage(stageId, "active");
                    addLog(`[${data.doc_index}/${data.doc_total}] Starting ${data.stage}...`, "info", data.stage);
                  } else if (data.event === "end") {
                    setStageProgress(prev => ({ ...prev, [data.stage]: 1 }));
                    updateStage(stageId, "completed");
                    const statsStr = data.stats
                      ? ` (${Object.entries(data.stats).map(([k, v]) => `${v} ${k}`).join(", ")})`
                      : "";
                    addLog(`[${data.doc_index}/${data.doc_total}] ✓ ${data.stage} complete${statsStr}`, "success", data.stage);
                  }
                } else if (data.type === "complete") {
                  setProgress(100);
                  addLog("", "dim");
                  addLog("═══════════════════════════════════════════", "success");
                  addLog("  PIPELINE COMPLETED SUCCESSFULLY", "success", "✓");
                  addLog("═══════════════════════════════════════════", "success");

                  // Extract stats from result
                  const result = data.result;
                  if (result?.log_file) {
                    setLogFile(result.log_file);
                    addLog(`Log file: ${result.log_file}`, "info");
                  }

                  const docsProcessed = result?.documents_processed?.length || 0;
                  setStats({
                    documents: docsProcessed,
                    molecules: result?.total_molecules || 0,
                    experiments: result?.total_experiments || 0,
                    results: result?.total_results || 0,
                  });

                  setCompleted(true);
                } else if (data.type === "error") {
                  addLog(`ERROR: ${data.error}`, "error", "✕");
                }
                // Ignore heartbeat, just updates lastUpdate
              } catch {
                // Ignore JSON parse errors for malformed chunks
              }
            }
          }
        }
      }
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      addLog(`ERROR: ${errorMessage}`, "error", "✕");
      updateStage(currentStage ? stageToId[currentStage] || "pdf" : "pdf", "error");
    } finally {
      setRunning(false);
    }
  };

  const canRun = useMemo(() => {
    return !!inputDir && !!outputDir && !!anthropic && !!primaryModel;
  }, [inputDir, outputDir, anthropic, primaryModel]);

  return (
    <div className="min-h-screen relative">
      {/* Background effects */}
      <div className="grid-background" />
      <div className="gradient-overlay" />

      {/* Main content */}
      <main className="relative z-10 max-w-7xl mx-auto p-6 space-y-6">

        {/* Header */}
        <header className="flex items-end justify-between gap-4 flex-wrap py-4">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="text-4xl">🧬</div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-emerald-400 bg-clip-text text-transparent">
                  KEVIN
                </h1>
                <p className="text-xs text-white/40 uppercase tracking-widest">
                  Multi-Model Chemistry Dataset Builder
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={runPipeline}
            disabled={!canRun || running}
            className="btn-primary flex items-center gap-3"
          >
            {running ? (
              <>
                <DNALoader />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <span>▶</span>
                <span>Run Pipeline</span>
              </>
            )}
          </button>
        </header>

        {/* Progress Section - Only visible when running or completed */}
        {(running || completed) && (
          <section className="glass-card p-6 fade-in">
            <ProgressBar
              progress={progress}
              stage={currentStage
                ? `${currentStage}${docTotal > 0 ? ` (Doc ${docIndex}/${docTotal})` : ""}`
                : "Initializing..."}
              isActive={running}
            />

            {/* Last update indicator */}
            {running && (
              <div className="text-xs text-white/40 mt-2 flex items-center justify-between">
                <span>
                  Last update: {Math.round((Date.now() - lastUpdate) / 1000)}s ago
                </span>
                {Date.now() - lastUpdate > 30000 && (
                  <span className="text-amber-400/80">
                    Still working, LLM calls can take a few minutes...
                  </span>
                )}
              </div>
            )}

            {/* Stats row */}
            {completed && (
              <div className="grid grid-cols-4 gap-4 mt-6 fade-in">
                <StatCard value={stats.documents} label="Documents" icon="📄" />
                <StatCard value={stats.molecules} label="Molecules" icon="🧬" />
                <StatCard value={stats.experiments} label="Experiments" icon="🧪" />
                <StatCard value={stats.results} label="Results" icon="📊" />
              </div>
            )}
          </section>
        )}

        {/* Main grid */}
        <div className="grid lg:grid-cols-3 gap-6">

          {/* Left column - Configuration */}
          <div className="lg:col-span-2 space-y-6">

            {/* API Keys */}
            <section className="glass-card glass-card-glow p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>🔑</span>
                <span>API Keys</span>
                <span className="text-xs text-white/40 font-normal ml-2">Stored locally in browser</span>
              </h2>
              <div className="grid sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Anthropic <span className="text-cyan-400">*required</span>
                  </label>
                  <input
                    type="password"
                    value={anthropic}
                    onChange={(e) => setAnthropic(e.target.value)}
                    placeholder="sk-ant-..."
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    OpenAI <span className="text-white/30">(audit)</span>
                  </label>
                  <input
                    type="password"
                    value={openai}
                    onChange={(e) => setOpenai(e.target.value)}
                    placeholder="sk-..."
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Google <span className="text-white/30">(gaps)</span>
                  </label>
                  <input
                    type="password"
                    value={gemini}
                    onChange={(e) => setGemini(e.target.value)}
                    placeholder="AIza..."
                    className="input-field"
                  />
                </div>
              </div>
            </section>

            {/* Folders */}
            <section className="glass-card glass-card-glow p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>📁</span>
                <span>Directories</span>
              </h2>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Input Folder <span className="text-cyan-400">*required</span>
                  </label>
                  <input
                    type="text"
                    value={inputDir}
                    onChange={(e) => setInputDir(e.target.value)}
                    placeholder="C:\Users\...\Kevin\input"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Output Folder <span className="text-cyan-400">*required</span>
                  </label>
                  <input
                    type="text"
                    value={outputDir}
                    onChange={(e) => setOutputDir(e.target.value)}
                    placeholder="C:\Users\...\Kevin\output"
                    className="input-field"
                  />
                </div>
              </div>
            </section>

            {/* Terminal */}
            <section className="fade-in">
              <Terminal
                lines={terminalLines}
                isRunning={running}
                title="Pipeline Output"
              />
            </section>
          </div>

          {/* Right column - Models & Stages */}
          <div className="space-y-6">

            {/* Models */}
            <section className="glass-card p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>🤖</span>
                <span>Models</span>
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Primary Extractor
                  </label>
                  <input
                    type="text"
                    value={primaryModel}
                    onChange={(e) => setPrimaryModel(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Auditor
                  </label>
                  <input
                    type="text"
                    value={auditorModel}
                    onChange={(e) => setAuditorModel(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Gap Hunter
                  </label>
                  <input
                    type="text"
                    value={gapModel}
                    onChange={(e) => setGapModel(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>
            </section>

            {/* Stage Tracker */}
            <section className="glass-card p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>📋</span>
                <span>Pipeline Stages</span>
              </h2>
              <StageTracker stages={stages} />
            </section>

            {/* Status */}
            <section className="glass-card p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>📡</span>
                <span>Status</span>
              </h2>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <span className={`w-3 h-3 rounded-full ${canRun ? "bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.5)]" : "bg-amber-400"}`} />
                  <span className="text-sm">
                    {canRun ? "Ready to run" : "Configure required fields"}
                  </span>
                </div>
                {!anthropic && (
                  <div className="text-xs text-amber-400/80">⚠ Anthropic API key required</div>
                )}
                {!inputDir && (
                  <div className="text-xs text-amber-400/80">⚠ Input folder required</div>
                )}
                {!outputDir && (
                  <div className="text-xs text-amber-400/80">⚠ Output folder required</div>
                )}
                {logFile && (
                  <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                    <div className="text-xs text-emerald-400 uppercase tracking-wider mb-1">Log File</div>
                    <div className="text-sm text-white/80 font-mono break-all">{logFile}</div>
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>

        {/* Footer */}
        <footer className="text-center text-xs text-white/30 py-8">
          <div className="flex items-center justify-center gap-2">
            <span>KEVIN v1.0</span>
            <span>•</span>
            <span>Multi-Model Chemistry Dataset Builder</span>
            <span>•</span>
            <span>2026</span>
          </div>
        </footer>
      </main>
    </div>
  );
}
