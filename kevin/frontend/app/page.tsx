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
  { id: "opus", name: "Opus Extraction", icon: "🧬" },
  { id: "audit", name: "GPT-5.2 Audit", icon: "🔍" },
  { id: "repair", name: "Auto-Repair", icon: "🔧" },
  { id: "gap", name: "Gemini Gap Hunt", icon: "🎯" },
  { id: "resolve", name: "Gap Resolution", icon: "✨" },
  { id: "export", name: "Export Dataset", icon: "💾" },
];

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

  // Simulate pipeline with SSE (or polling in real implementation)
  const runPipeline = async () => {
    setRunning(true);
    setCompleted(false);
    setProgress(0);
    setTerminalLines([]);
    setStages(PIPELINE_STAGES.map(s => ({ ...s, status: "pending" as const, detail: "" })));
    setStats({ molecules: 0, experiments: 0, results: 0, documents: 0 });
    setLogFile("");

    addLog("Initializing Kevin Pipeline v1.0", "system", "SYSTEM");
    addLog(`Input: ${inputDir}`, "dim");
    addLog(`Output: ${outputDir}`, "dim");
    addLog("", "dim");

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

      addLog("Connecting to backend server...", "info", "NET");

      const response = await fetch("http://localhost:8787/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      // In a real implementation, you'd use SSE or WebSockets for real-time updates
      // For now, we'll simulate the progress after getting the response
      const result = await response.json();

      // Simulate progressive updates (in production, these would come from SSE)
      await simulateProgress(result);

      if (result.ok) {
        addLog("", "dim");
        addLog("═══════════════════════════════════════════", "success");
        addLog("  PIPELINE COMPLETED SUCCESSFULLY", "success", "✓");
        addLog("═══════════════════════════════════════════", "success");

        if (result.log_file) {
          setLogFile(result.log_file);
          addLog(`Log file: ${result.log_file}`, "info");
        }

        setCompleted(true);
      } else {
        throw new Error(result.run?.errors?.[0]?.error || "Pipeline failed");
      }

    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      addLog(`ERROR: ${errorMessage}`, "error", "✕");
      updateStage(currentStage || "pdf", "error");
    } finally {
      setRunning(false);
    }
  };

  // Simulate progress updates (replace with real SSE in production)
  const simulateProgress = async (result: Record<string, unknown>) => {
    const stageProgress = [
      { id: "pdf", progress: 15, delay: 500 },
      { id: "opus", progress: 35, delay: 2000 },
      { id: "audit", progress: 55, delay: 1500 },
      { id: "repair", progress: 70, delay: 1000 },
      { id: "gap", progress: 85, delay: 1500 },
      { id: "resolve", progress: 95, delay: 1000 },
      { id: "export", progress: 100, delay: 500 },
    ];

    for (const stage of stageProgress) {
      setCurrentStage(stage.id);
      updateStage(stage.id, "active");

      const stageInfo = PIPELINE_STAGES.find(s => s.id === stage.id);
      addLog(`Starting ${stageInfo?.name}...`, "info", stage.id.toUpperCase());

      await new Promise(r => setTimeout(r, stage.delay));

      setProgress(stage.progress);
      updateStage(stage.id, "completed");
      addLog(`${stageInfo?.name} completed`, "success", stage.id.toUpperCase());
    }

    // Update final stats from result
    const run = result.run as Record<string, unknown> | undefined;
    const docsProcessed = run?.documents_processed as string[] | undefined;
    const docs = docsProcessed?.length || 0;
    setStats({
      documents: docs,
      molecules: Math.floor(Math.random() * 20) + 5, // Replace with real data
      experiments: Math.floor(Math.random() * 15) + 3,
      results: Math.floor(Math.random() * 50) + 10,
    });
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
              stage={currentStage ? PIPELINE_STAGES.find(s => s.id === currentStage)?.name || "" : "Initializing..."}
              isActive={running}
            />

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
