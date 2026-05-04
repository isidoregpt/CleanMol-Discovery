"use client";

import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { ProgressBar } from "./components/ProgressBar";
import { Terminal, TerminalLine } from "./components/Terminal";
import { StageTracker } from "./components/StageTracker";
import { StatCard } from "./components/StatCard";
import { DNALoader } from "./components/DNALoader";
import { getDefaults, resolveLatestDefaults } from "./api";
import type { DefaultsResponse, ModelBundle } from "./api";

const LS = {
  openai: "cleanmol:key:openai",
  anthropic: "cleanmol:key:anthropic",
  gemini: "cleanmol:key:gemini",
  hf: "cleanmol:key:hf",
  models: "cleanmol:models",
  autoLatestModels: "cleanmol:models:autoLatest",
  paths: "cleanmol:paths"
};

const FALLBACK_MODEL_DEFAULTS: ModelBundle = {
  primary: "claude-opus-4-7",
  auditor: "gpt-5.5",
  gapHunter: "gemini-3.1-pro-preview",
  figure: "claude-opus-4-7"
};

const FALLBACK_MODEL_DEFAULTS_LAST_VERIFIED = "2026-05-04";

const FALLBACK_LEGACY_MODEL_ALIASES: Record<string, string> = {
  "claude-opus-4-5-20251101": FALLBACK_MODEL_DEFAULTS.primary,
  "claude-opus-4-20250514": FALLBACK_MODEL_DEFAULTS.primary,
  "claude-opus-4-1-20250805": FALLBACK_MODEL_DEFAULTS.primary,
  "gpt-5.2": FALLBACK_MODEL_DEFAULTS.auditor,
  "gpt-5.2-thinking": FALLBACK_MODEL_DEFAULTS.auditor,
  "gpt-5.2-2025-12-11": FALLBACK_MODEL_DEFAULTS.auditor,
  "gemini-3-pro": FALLBACK_MODEL_DEFAULTS.gapHunter,
  "gemini-3-pro-preview": FALLBACK_MODEL_DEFAULTS.gapHunter
};

function normalizeModelId(
  value: unknown,
  fallback: string,
  aliases: Record<string, string> = FALLBACK_LEGACY_MODEL_ALIASES
) {
  const model = typeof value === "string" ? value.trim() : "";
  if (!model) return fallback;
  return aliases[model] || model;
}

const PIPELINE_STAGES = [
  { id: "pdf", name: "PDF Extraction", icon: "1" },
  { id: "figure", name: "Figure Analysis", icon: "2" },
  { id: "opus", name: "Primary Extraction", icon: "3" },
  { id: "audit", name: "OpenAI Audit", icon: "4" },
  { id: "repair", name: "Auto-Repair", icon: "5" },
  { id: "gap", name: "Gemini Gap Hunt", icon: "6" },
  { id: "resolve", name: "Gap Resolution", icon: "7" },
  { id: "smiles", name: "SMILES Lookup", icon: "8" },
  { id: "validate", name: "SMILES Validation", icon: "9" },
  { id: "export", name: "Export Dataset", icon: "10" },
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

type StageStatus = "pending" | "active" | "completed" | "error";
type StageState = (typeof PIPELINE_STAGES)[number] & {
  status: StageStatus;
  detail: string;
};
type DiscoveryMode = "auto" | "upload";
type DiscoveryResult = {
  ok?: boolean;
  summary?: Record<string, unknown>;
  files?: Record<string, string>;
  dataset_quality?: {
    status?: string;
    status_label?: string;
    quality_score?: number;
    gates_passed?: number;
    gates_total?: number;
    recommendations?: string[];
  };
  top_candidates?: Array<Record<string, unknown>>;
};
type OnlineSource = {
  id: string;
  name: string;
  connector: string;
  dataset_id?: string;
  role?: string;
  domain_fit?: string;
  modernity?: string;
  pull_supported?: boolean;
  default_selected?: boolean;
  source_url?: string;
  use_guidance?: string;
};
type ModelKey = "primary" | "auditor" | "gapHunter";
type InfoPanel = "instructions" | "about" | "license";

// Creep function: starts fast, slows down, never reaches cap
function creepProgress(elapsedMs: number, cap = 0.92, speed = 0.0003): number {
  return cap * (1 - Math.exp(-speed * elapsedMs));
}

export default function Page() {
  // API Keys
  const [openai, setOpenai] = useState("");
  const [anthropic, setAnthropic] = useState("");
  const [gemini, setGemini] = useState("");
  const [hfToken, setHfToken] = useState("");

  // Models
  const [modelDefaults, setModelDefaults] = useState<ModelBundle>(FALLBACK_MODEL_DEFAULTS);
  const [modelDefaultsVerified, setModelDefaultsVerified] = useState(FALLBACK_MODEL_DEFAULTS_LAST_VERIFIED);
  const [primaryModel, setPrimaryModel] = useState(FALLBACK_MODEL_DEFAULTS.primary);
  const [auditorModel, setAuditorModel] = useState(FALLBACK_MODEL_DEFAULTS.auditor);
  const [gapModel, setGapModel] = useState(FALLBACK_MODEL_DEFAULTS.gapHunter);
  const [autoLatestModels, setAutoLatestModels] = useState(true);
  const [modelRefreshRunning, setModelRefreshRunning] = useState(false);
  const [modelRefreshStatus, setModelRefreshStatus] = useState("");
  const modelDefaultsRef = useRef<ModelBundle>(FALLBACK_MODEL_DEFAULTS);

  // Paths
  const [inputDir, setInputDir] = useState("");
  const [outputDir, setOutputDir] = useState("");

  // Pipeline state
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState("");
  const [terminalLines, setTerminalLines] = useState<TerminalLine[]>([]);
  const [stages, setStages] = useState<StageState[]>(
    PIPELINE_STAGES.map(s => ({ ...s, status: "pending" as const, detail: "" }))
  );

  // Streaming progress state
  const [docIndex, setDocIndex] = useState(0);
  const [docTotal, setDocTotal] = useState(0);
  const [stageStartTime, setStageStartTime] = useState<number | null>(null);
  const [stageProgress, setStageProgress] = useState<Record<string, number>>({});
  const [lastUpdate, setLastUpdate] = useState(Date.now());

  // Discovery automation state
  const [discoveryMode, setDiscoveryMode] = useState<DiscoveryMode>("auto");
  const [includePublicSources, setIncludePublicSources] = useState(true);
  const [allowBuiltinGenerator, setAllowBuiltinGenerator] = useState(true);
  const [targetCandidateCount, setTargetCandidateCount] = useState(50);
  const [uploadedDatasetPath, setUploadedDatasetPath] = useState("");
  const [uploadingDataset, setUploadingDataset] = useState(false);
  const [discoveryRunning, setDiscoveryRunning] = useState(false);
  const [discoveryCompleted, setDiscoveryCompleted] = useState(false);
  const [discoveryResult, setDiscoveryResult] = useState<DiscoveryResult | null>(null);
  const [discoveryLines, setDiscoveryLines] = useState<TerminalLine[]>([]);
  const [sourceCatalog, setSourceCatalog] = useState<OnlineSource[]>([]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const [sourceQuery, setSourceQuery] = useState("antimicrobial SMILES MIC");
  const [sourceSearchResults, setSourceSearchResults] = useState<OnlineSource[]>([]);
  const [sourceLoading, setSourceLoading] = useState(false);

  // Results
  const [stats, setStats] = useState({
    molecules: 0,
    experiments: 0,
    results: 0,
    documents: 0,
  });
  const [completed, setCompleted] = useState(false);
  const [logFile, setLogFile] = useState("");
  const [infoPanel, setInfoPanel] = useState<InfoPanel>("instructions");

  const applyDefaultPayload = useCallback((data: DefaultsResponse, force = false) => {
    const previousDefaults = modelDefaultsRef.current;
    const models = { ...FALLBACK_MODEL_DEFAULTS, ...(data.models || {}) };
    const aliases = { ...FALLBACK_LEGACY_MODEL_ALIASES, ...(data.legacy_model_aliases || {}) };

    const updateCurrentModel = (current: string, key: ModelKey) => {
      const nextDefault = models[key] || FALLBACK_MODEL_DEFAULTS[key];
      const normalized = normalizeModelId(current, nextDefault, aliases);
      if (
        force ||
        !current ||
        current === previousDefaults[key] ||
        current === FALLBACK_MODEL_DEFAULTS[key] ||
        normalized !== current
      ) {
        return normalized || nextDefault;
      }
      return current;
    };

    setModelDefaults(models);
    modelDefaultsRef.current = models;
    if (data.model_defaults_last_verified) {
      setModelDefaultsVerified(data.model_defaults_last_verified);
    }

    setPrimaryModel((current) => updateCurrentModel(current, "primary"));
    setAuditorModel((current) => updateCurrentModel(current, "auditor"));
    setGapModel((current) => updateCurrentModel(current, "gapHunter"));
  }, []);

  const refreshLatestModelDefaults = useCallback(async (force = false, quiet = false) => {
    const hasProviderKey = [openai, anthropic, gemini].some(key => key.trim().length >= 12);
    if (!hasProviderKey) {
      if (!quiet) setModelRefreshStatus("Add provider API keys to refresh latest model defaults.");
      return;
    }

    setModelRefreshRunning(true);
    if (!quiet) setModelRefreshStatus("Checking provider model lists...");
    try {
      const data = await resolveLatestDefaults({ openai, anthropic, gemini });
      applyDefaultPayload(data, force);
      const resolved = Object.values(data.resolution || {}).filter(item => item.status === "resolved").length;
      setModelRefreshStatus(
        resolved
          ? `Latest provider defaults refreshed (${resolved} role${resolved === 1 ? "" : "s"} resolved).`
          : "Provider refresh completed; using verified fallback defaults."
      );
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      setModelRefreshStatus(`Latest model refresh failed; using verified fallbacks. ${errorMessage}`);
    } finally {
      setModelRefreshRunning(false);
    }
  }, [anthropic, applyDefaultPayload, gemini, openai]);

  // Load saved settings
  useEffect(() => {
    if (typeof window === "undefined") return;

    setOpenai(localStorage.getItem(LS.openai) || "");
    setAnthropic(localStorage.getItem(LS.anthropic) || "");
    setGemini(localStorage.getItem(LS.gemini) || "");
    setHfToken(localStorage.getItem(LS.hf) || "");
    setAutoLatestModels(localStorage.getItem(LS.autoLatestModels) !== "false");

    const m = localStorage.getItem(LS.models);
    if (m) {
      try {
        const j = JSON.parse(m);
        setPrimaryModel(normalizeModelId(j.primary, FALLBACK_MODEL_DEFAULTS.primary));
        setAuditorModel(normalizeModelId(j.auditor, FALLBACK_MODEL_DEFAULTS.auditor));
        setGapModel(normalizeModelId(j.gapHunter || j.gap, FALLBACK_MODEL_DEFAULTS.gapHunter));
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
    let cancelled = false;

    getDefaults()
      .then((data) => {
        if (cancelled) return;
        applyDefaultPayload(data);
      })
      .catch(() => {
        // The local backend may still be starting; the pinned frontend fallback stays usable.
      });

    return () => {
      cancelled = true;
    };
  }, [applyDefaultPayload]);

  useEffect(() => {
    if (!autoLatestModels || ![openai, anthropic, gemini].some(key => key.trim().length >= 12)) return;
    const timeout = window.setTimeout(() => {
      refreshLatestModelDefaults(true, true);
    }, 1000);
    return () => window.clearTimeout(timeout);
  }, [anthropic, autoLatestModels, gemini, openai, refreshLatestModelDefaults]);

  // Save settings
  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(LS.openai, openai);
    localStorage.setItem(LS.anthropic, anthropic);
    localStorage.setItem(LS.gemini, gemini);
    localStorage.setItem(LS.hf, hfToken);
  }, [openai, anthropic, gemini, hfToken]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(LS.autoLatestModels, autoLatestModels ? "true" : "false");
  }, [autoLatestModels]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(LS.models, JSON.stringify({
      primary: primaryModel,
      auditor: auditorModel,
      gapHunter: gapModel
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

  const addDiscoveryLog = useCallback((text: string, type: TerminalLine["type"] = "info", prefix?: string) => {
    const timestamp = new Date().toLocaleTimeString("en-US", { hour12: false });
    setDiscoveryLines(prev => [...prev, { timestamp, type, prefix, text }]);
  }, []);

  const loadSourceCatalog = useCallback(async () => {
    setSourceLoading(true);
    try {
      const response = await fetch("http://localhost:8787/api/discovery/source-catalog");
      if (!response.ok) throw new Error(`Source catalog error: ${response.status}`);
      const data = await response.json();
      const sources = (data.sources || []) as OnlineSource[];
      setSourceCatalog(sources);
      setSelectedSourceIds(prev => prev.length ? prev : (data.default_source_ids || []));
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      addDiscoveryLog(`ERROR: ${errorMessage}`, "error", "SOURCES");
    } finally {
      setSourceLoading(false);
    }
  }, [addDiscoveryLog]);

  const searchOnlineSources = useCallback(async () => {
    if (!sourceQuery.trim()) return;
    setSourceLoading(true);
    try {
      const response = await fetch("http://localhost:8787/api/discovery/source-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: sourceQuery,
          limit: 10,
          keys: { hf: hfToken },
        }),
      });
      if (!response.ok) throw new Error(`Source search error: ${response.status}`);
      const data = await response.json();
      setSourceSearchResults((data.results || []) as OnlineSource[]);
      addDiscoveryLog(`Found ${(data.results || []).length} online source candidates`, "success", "SOURCES");
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      addDiscoveryLog(`ERROR: ${errorMessage}`, "error", "SOURCES");
    } finally {
      setSourceLoading(false);
    }
  }, [addDiscoveryLog, hfToken, sourceQuery]);

  const toggleSource = (sourceId: string) => {
    setSelectedSourceIds(prev =>
      prev.includes(sourceId) ? prev.filter(id => id !== sourceId) : [...prev, sourceId]
    );
  };

  useEffect(() => {
    loadSourceCatalog();
  }, [loadSourceCatalog]);

  // Update stage status
  const updateStage = useCallback((stageId: string, status: StageStatus, detail?: string) => {
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

    addLog("Initializing CleanMol Pipeline v1.0", "system", "SYSTEM");
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
          options: { max_gap_rounds: 2, resolve_latest_models: autoLatestModels }
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
                    addLog(`[${data.doc_index}/${data.doc_total}] OK ${data.stage} complete${statsStr}`, "success", data.stage);
                  }
                } else if (data.type === "complete") {
                  setProgress(100);
                  addLog("", "dim");
                  addLog("===========================================", "success");
                  addLog("  PIPELINE COMPLETED SUCCESSFULLY", "success", "OK");
                  addLog("===========================================", "success");

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
                  addLog(`ERROR: ${data.error}`, "error", "ERR");
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
      addLog(`ERROR: ${errorMessage}`, "error", "ERR");
      updateStage(currentStage ? stageToId[currentStage] || "pdf" : "pdf", "error");
    } finally {
      setRunning(false);
    }
  };

  const uploadDiscoveryDataset = async (file: File | null) => {
    if (!file) return;
    if (!outputDir) {
      addDiscoveryLog("Set an output folder before uploading a dataset.", "error", "UPLOAD");
      return;
    }

    setUploadingDataset(true);
    try {
      const form = new FormData();
      form.append("output_dir", outputDir);
      form.append("file", file);
      addDiscoveryLog(`Uploading dataset: ${file.name}`, "info", "UPLOAD");

      const response = await fetch("http://localhost:8787/api/discovery/upload-dataset", {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }
      const data = await response.json();
      setUploadedDatasetPath(data.path || "");
      addDiscoveryLog(`Uploaded dataset saved to ${data.path}`, "success", "UPLOAD");
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      addDiscoveryLog(`ERROR: ${errorMessage}`, "error", "UPLOAD");
    } finally {
      setUploadingDataset(false);
    }
  };

  const runDiscovery = async () => {
    setDiscoveryRunning(true);
    setDiscoveryCompleted(false);
    setDiscoveryResult(null);
    setDiscoveryLines([]);

    addDiscoveryLog("Starting automated Discovery workflow", "system", "DISCOVERY");
    addDiscoveryLog(`Output: ${outputDir}`, "dim");
    addDiscoveryLog(`Mode: ${discoveryMode}`, "dim");
    if (uploadedDatasetPath) addDiscoveryLog(`Uploaded dataset: ${uploadedDatasetPath}`, "dim");

    let buffer = "";

    try {
      const response = await fetch("http://localhost:8787/api/discovery/run-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          output_dir: outputDir,
          uploaded_dataset_path: discoveryMode === "upload" ? uploadedDatasetPath : undefined,
          keys: { hf: hfToken },
          options: {
            mode: discoveryMode,
            include_public_sources: includePublicSources,
            selected_source_ids: selectedSourceIds,
            allow_builtin_generator: allowBuiltinGenerator,
            target_candidate_count: targetCandidateCount,
            generator_engine: "auto",
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No response body");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          for (const line of event.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === "discovery_progress") {
                const statsStr = Object.entries(data)
                  .filter(([key]) => !["type", "stage", "event", "message"].includes(key))
                  .map(([key, value]) => `${key}=${value}`)
                  .join(", ");
                const message = data.message || `${data.stage} ${data.event}${statsStr ? ` (${statsStr})` : ""}`;
                addDiscoveryLog(message, data.event === "end" ? "success" : "info", data.stage);
              } else if (data.type === "discovery_complete") {
                setDiscoveryResult(data.result);
                setDiscoveryCompleted(true);
                addDiscoveryLog("Discovery workflow completed", "success", "DONE");
                const files = data.result?.files || {};
                Object.entries(files).forEach(([name, path]) => {
                  addDiscoveryLog(`${name}: ${path}`, "info", "FILE");
                });
              } else if (data.type === "error") {
                addDiscoveryLog(`ERROR: ${data.error}`, "error", "ERROR");
              }
            } catch {
              // Ignore malformed chunks.
            }
          }
        }
      }
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      addDiscoveryLog(`ERROR: ${errorMessage}`, "error", "ERROR");
    } finally {
      setDiscoveryRunning(false);
    }
  };

  const canRun = useMemo(() => {
    return !!inputDir && !!outputDir && !!anthropic && !!primaryModel;
  }, [inputDir, outputDir, anthropic, primaryModel]);

  const pipelineIssues = useMemo(() => {
    const issues: string[] = [];
    if (!anthropic) issues.push("Anthropic API key");
    if (!inputDir) issues.push("input folder with PDFs");
    if (!outputDir) issues.push("output folder");
    if (!primaryModel) issues.push("primary model");
    return issues;
  }, [anthropic, inputDir, outputDir, primaryModel]);

  const discoveryIssues = useMemo(() => {
    const issues: string[] = [];
    if (!outputDir) issues.push("output folder");
    if (discoveryMode === "upload" && !uploadedDatasetPath) {
      issues.push("uploaded CSV or Excel dataset");
    }
    return issues;
  }, [discoveryMode, outputDir, uploadedDatasetPath]);

  const canRunDiscovery = useMemo(() => {
    return discoveryIssues.length === 0 && !discoveryRunning && !running;
  }, [discoveryIssues.length, discoveryRunning, running]);

  const useModelDefaults = () => {
    setPrimaryModel(modelDefaults.primary);
    setAuditorModel(modelDefaults.auditor);
    setGapModel(modelDefaults.gapHunter);
  };

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
              <div className="h-12 w-12 rounded-xl border border-cyan-300/30 bg-cyan-400/10 flex items-center justify-center text-sm font-bold tracking-widest text-cyan-200">
                CM
              </div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-emerald-400 bg-clip-text text-transparent">
                  CleanMol Discovery
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
              <span>Run Pipeline</span>
            )}
          </button>
        </header>

        <section className="glass-card p-5">
          <div className="flex items-center justify-between gap-4 flex-wrap mb-4">
            <div>
              <h2 className="text-lg font-semibold">Research Guide</h2>
              <p className="text-sm text-white/50">
                Start with the workflow you need; CleanMol will show the required folders and keys for that path.
              </p>
            </div>
            <div className="flex gap-2">
              {(["instructions", "about", "license"] as InfoPanel[]).map(panel => (
                <button
                  key={panel}
                  type="button"
                  onClick={() => setInfoPanel(panel)}
                  className={`px-3 py-2 rounded-lg border text-sm transition ${
                    infoPanel === panel
                      ? "border-cyan-400/50 bg-cyan-500/15 text-cyan-100"
                      : "border-white/10 bg-white/5 text-white/65 hover:bg-white/10"
                  }`}
                >
                  {panel === "instructions" ? "Instructions" : panel === "about" ? "About" : "License"}
                </button>
              ))}
            </div>
          </div>

          {infoPanel === "instructions" && (
            <div className="grid md:grid-cols-3 gap-4 text-sm text-white/70">
              <div>
                <div className="text-xs uppercase tracking-wider text-cyan-300/80 mb-2">1. Choose a path</div>
                <p>Use Run Pipeline when you have PDFs. Use Discovery Automation when you want candidates from public, generated, or uploaded data.</p>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-cyan-300/80 mb-2">2. Set folders</div>
                <p>Pipeline needs input and output folders. Discovery only needs an output folder; Chemist upload also needs a CSV or Excel file.</p>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-cyan-300/80 mb-2">3. Review outputs</div>
                <p>Open the ranked CSV and Excel review packet before any synthesis, safety review, or lab testing decision. Use the FAIR Chemistry UMA file only after charge, spin, and fragments are reviewed.</p>
              </div>
            </div>
          )}

          {infoPanel === "about" && (
            <p className="text-sm text-white/70">
              CleanMol Discovery builds auditable chemistry datasets and ranked disinfectant candidate packets for next-generation antimicrobial research. It is meant to help researchers without large private datasets get a serious starting point while keeping provenance, quality gates, and review files visible. It also prepares a FAIR Chemistry / UMA handoff file for optional atomistic physics review after candidates are ranked.
            </p>
          )}

          {infoPanel === "license" && (
            <p className="text-sm text-white/70">
              Free for research, education, nonprofit, and individual use under the CleanMol Discovery Research License. Commercial use, resale, hosted services, private-label distribution, or commercialization of outputs requires a separate written commercial license. Publications and discoveries materially using CleanMol must credit CleanMol Discovery by Jonathan Graziola.
            </p>
          )}
        </section>

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
                <StatCard value={stats.documents} label="Documents" icon="DOC" />
                <StatCard value={stats.molecules} label="Molecules" icon="MOL" />
                <StatCard value={stats.experiments} label="Experiments" icon="EXP" />
                <StatCard value={stats.results} label="Results" icon="RES" />
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
                <span>API Keys</span>
                <span className="text-xs text-white/40 font-normal ml-2">Stored locally in browser</span>
              </h2>
              <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
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
                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Hugging Face <span className="text-white/30">(datasets)</span>
                  </label>
                  <input
                    type="password"
                    value={hfToken}
                    onChange={(e) => setHfToken(e.target.value)}
                    placeholder="hf_..."
                    className="input-field"
                  />
                </div>
              </div>
            </section>

            {/* Folders */}
            <section className="glass-card glass-card-glow p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>Directories</span>
              </h2>
              <p className="text-sm text-white/50 mb-4">
                Pipeline extraction needs both folders. Discovery Automation only needs the output folder; Chemist upload also needs the dataset file.
              </p>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Input Folder <span className="text-white/30">(pipeline only)</span>
                  </label>
                  <input
                    type="text"
                    value={inputDir}
                    onChange={(e) => setInputDir(e.target.value)}
                    placeholder="C:\Users\...\CleanMol\input"
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
                    placeholder="C:\Users\...\CleanMol\output"
                    className="input-field"
                  />
                </div>
              </div>
            </section>

            {/* Discovery Automation */}
            <section className="glass-card glass-card-glow p-6">
              <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
                <h2 className="text-lg font-semibold">Discovery Automation</h2>
                <button
                  type="button"
                  onClick={runDiscovery}
                  disabled={!canRunDiscovery}
                  className="btn-primary flex items-center gap-3"
                >
                  <span>{discoveryRunning ? "Running..." : "Run Discovery"}</span>
                </button>
              </div>
              <p className="text-sm text-white/55 mb-4">
                Auto-create can start with only an output folder. Chemist upload uses your CSV or Excel file and then applies the same quality gates.
              </p>

              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Dataset Mode
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setDiscoveryMode("auto")}
                      className={`px-3 py-2 rounded-lg border transition text-sm ${
                        discoveryMode === "auto"
                          ? "bg-cyan-500/20 border-cyan-400/50 text-cyan-100"
                          : "bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
                      }`}
                    >
                      Auto-create
                    </button>
                    <button
                      type="button"
                      onClick={() => setDiscoveryMode("upload")}
                      className={`px-3 py-2 rounded-lg border transition text-sm ${
                        discoveryMode === "upload"
                          ? "bg-cyan-500/20 border-cyan-400/50 text-cyan-100"
                          : "bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
                      }`}
                    >
                      Chemist upload
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Candidate Count
                  </label>
                  <input
                    type="number"
                    min={10}
                    max={500}
                    value={targetCandidateCount}
                    onChange={(e) => setTargetCandidateCount(Math.max(10, Math.min(500, Number(e.target.value) || 50)))}
                    className="input-field"
                  />
                </div>
              </div>

              {discoveryMode === "upload" && (
                <div className="mb-4">
                  <label className="block text-xs text-white/50 uppercase tracking-wider mb-2">
                    Upload CSV or Excel Dataset
                  </label>
                  <input
                    type="file"
                    accept=".csv,.tsv,.xlsx,.xlsm"
                    disabled={uploadingDataset || !outputDir}
                    onChange={(e) => uploadDiscoveryDataset(e.target.files?.[0] || null)}
                    className="input-field"
                  />
                  {uploadedDatasetPath && (
                    <div className="text-xs text-emerald-300/80 mt-2 break-all">
                      Loaded: {uploadedDatasetPath}
                    </div>
                  )}
                  {!outputDir && (
                    <div className="text-xs text-amber-300/80 mt-2">
                      Choose an output folder first so CleanMol has a safe place to save the uploaded dataset.
                    </div>
                  )}
                </div>
              )}

              <div className="grid sm:grid-cols-2 gap-3 mb-4">
                <label className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80">
                  <input
                    type="checkbox"
                    checked={includePublicSources}
                    onChange={(e) => setIncludePublicSources(e.target.checked)}
                  />
                  <span>Use public HF/API sources</span>
                </label>
                <label className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80">
                  <input
                    type="checkbox"
                    checked={allowBuiltinGenerator}
                    onChange={(e) => setAllowBuiltinGenerator(e.target.checked)}
                  />
                  <span>Allow built-in generator fallback</span>
                </label>
              </div>

              {includePublicSources && (
                <div className="space-y-4 mb-4">
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <h3 className="text-sm font-semibold text-white/80">Source Library</h3>
                    <button
                      type="button"
                      onClick={loadSourceCatalog}
                      disabled={sourceLoading}
                      className="text-xs px-3 py-2 rounded-lg bg-white/10 hover:bg-white/15 border border-white/10 transition"
                    >
                      Refresh
                    </button>
                  </div>

                  <div className="grid md:grid-cols-2 gap-3">
                    {sourceCatalog.map(source => (
                      <button
                        key={source.id}
                        type="button"
                        onClick={() => toggleSource(source.id)}
                        className={`text-left rounded-lg border p-3 transition ${
                          selectedSourceIds.includes(source.id)
                            ? "border-cyan-400/50 bg-cyan-500/10"
                            : "border-white/10 bg-white/5 hover:bg-white/10"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-medium text-white/90">{source.name}</span>
                          <span className="text-[10px] uppercase text-white/40">{source.connector}</span>
                        </div>
                        <div className="text-xs text-white/50 mt-1">
                          {source.role} - {source.modernity}
                        </div>
                        <div className="text-xs text-white/40 mt-1">
                          {source.domain_fit}
                        </div>
                      </button>
                    ))}
                  </div>

                  <div className="grid md:grid-cols-[1fr_auto] gap-2">
                    <input
                      type="text"
                      value={sourceQuery}
                      onChange={(e) => setSourceQuery(e.target.value)}
                      className="input-field"
                      placeholder="Search Hugging Face datasets"
                    />
                    <button
                      type="button"
                      onClick={searchOnlineSources}
                      disabled={sourceLoading || !sourceQuery.trim()}
                      className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 border border-white/10 transition text-sm"
                    >
                      Search
                    </button>
                  </div>

                  {sourceSearchResults.length > 0 && (
                    <div className="grid md:grid-cols-2 gap-3">
                      {sourceSearchResults.map(source => (
                        <button
                          key={source.id}
                          type="button"
                          onClick={() => toggleSource(source.id)}
                          className={`text-left rounded-lg border p-3 transition ${
                            selectedSourceIds.includes(source.id)
                              ? "border-emerald-400/50 bg-emerald-500/10"
                              : "border-white/10 bg-white/5 hover:bg-white/10"
                          }`}
                        >
                          <div className="text-sm font-medium text-white/90 break-all">{source.name}</div>
                          <div className="text-xs text-white/50 mt-1">
                            {source.domain_fit} - {source.modernity}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {(discoveryRunning || discoveryCompleted || discoveryLines.length > 0) && (
                <div className="mt-4">
                  <Terminal
                    lines={discoveryLines}
                    isRunning={discoveryRunning}
                    title="Discovery Output"
                  />
                </div>
              )}

              {discoveryResult?.summary && (
                <>
                  <div className="grid sm:grid-cols-4 gap-3 mt-4">
                    <StatCard value={Number(discoveryResult.summary.activity_rows || 0)} label="Activity Rows" icon="A" />
                    <StatCard value={Number(discoveryResult.summary.toxicity_rows || 0)} label="Toxicity Rows" icon="T" />
                    <StatCard value={Number(discoveryResult.summary.generated_count || 0)} label="Generated" icon="G" />
                    <StatCard value={Number(discoveryResult.summary.ranked_count || 0)} label="Ranked" icon="R" />
                  </div>

                  {discoveryResult.dataset_quality && (
                    <div className="mt-4 rounded-lg border border-white/10 bg-white/5 p-4">
                      <div className="flex items-center justify-between gap-3 flex-wrap">
                        <div>
                          <div className="text-xs uppercase tracking-wider text-white/40">Dataset Quality Equalizer</div>
                          <div className="text-xl font-semibold text-white/90">
                            {discoveryResult.dataset_quality.status_label || "Not Rated"}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-cyan-300">
                            {Number(discoveryResult.dataset_quality.quality_score || 0).toFixed(0)}
                          </div>
                          <div className="text-xs text-white/40">
                            {discoveryResult.dataset_quality.gates_passed || 0}/{discoveryResult.dataset_quality.gates_total || 0} gates
                          </div>
                        </div>
                      </div>
                      {!!discoveryResult.dataset_quality.recommendations?.length && (
                        <div className="mt-3 space-y-1">
                          {discoveryResult.dataset_quality.recommendations.slice(0, 3).map((rec, idx) => (
                            <div key={idx} className="text-xs text-white/55">
                              {rec}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
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
              <div className="flex items-center justify-between gap-3 mb-4">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <span>Models</span>
                </h2>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => refreshLatestModelDefaults(true)}
                    disabled={modelRefreshRunning}
                    className="text-xs px-3 py-2 rounded-lg bg-cyan-400/10 hover:bg-cyan-400/15 border border-cyan-300/20 transition disabled:opacity-50"
                  >
                    {modelRefreshRunning ? "Checking..." : "Refresh latest"}
                  </button>
                  <button
                    type="button"
                    onClick={useModelDefaults}
                    className="text-xs px-3 py-2 rounded-lg bg-white/10 hover:bg-white/15 border border-white/10 transition"
                  >
                    Use defaults
                  </button>
                </div>
              </div>
              <p className="text-xs text-white/45 mb-4">
                Defaults auto-refresh from provider model lists when keys are available; verified fallback {modelDefaultsVerified}.
              </p>
              <label className="flex items-center gap-2 text-xs text-white/55 mb-4">
                <input
                  type="checkbox"
                  checked={autoLatestModels}
                  onChange={(e) => setAutoLatestModels(e.target.checked)}
                  className="h-4 w-4 accent-cyan-400"
                />
                <span>Use latest provider models by default</span>
              </label>
              {modelRefreshStatus && (
                <div className="mb-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/55">
                  {modelRefreshStatus}
                </div>
              )}
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
                <span>Pipeline Stages</span>
              </h2>
              <StageTracker stages={stages} />
            </section>

            {/* Status */}
            <section className="glass-card p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>Status</span>
              </h2>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <span className={`w-3 h-3 rounded-full ${canRun ? "bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.5)]" : "bg-amber-400"}`} />
                  <span className="text-sm">
                    Pipeline: {canRun ? "ready" : "needs setup"}
                  </span>
                </div>
                {pipelineIssues.map(issue => (
                  <div key={issue} className="text-xs text-amber-400/80">
                    Pipeline needs: {issue}
                  </div>
                ))}
                <div className="flex items-center gap-3 pt-2">
                  <span className={`w-3 h-3 rounded-full ${canRunDiscovery ? "bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.5)]" : "bg-amber-400"}`} />
                  <span className="text-sm">
                    Discovery: {canRunDiscovery ? "ready" : "needs setup"}
                  </span>
                </div>
                {discoveryIssues.map(issue => (
                  <div key={issue} className="text-xs text-amber-400/80">
                    Discovery needs: {issue}
                  </div>
                ))}
                {discoveryMode === "auto" && !inputDir && (
                  <div className="text-xs text-white/45">
                    Auto-create discovery does not require an input folder.
                  </div>
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
            <span>CleanMol Discovery v1.0</span>
            <span>|</span>
            <span>Multi-Model Chemistry Dataset Builder</span>
            <span>|</span>
            <a
              href="https://github.com/isidoregpt/CleanMol-Discovery"
              target="_blank"
              rel="noreferrer"
              className="text-cyan-300/70 hover:text-cyan-200 transition"
            >
              Source / Research License
            </a>
            <span>|</span>
            <span>2026</span>
          </div>
        </footer>
      </main>
    </div>
  );
}
