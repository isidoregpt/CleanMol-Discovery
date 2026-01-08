"use client";

interface Stage {
  id: string;
  name: string;
  icon: string;
  status: "pending" | "active" | "completed" | "error";
  detail?: string;
}

interface StageTrackerProps {
  stages: Stage[];
}

export function StageTracker({ stages }: StageTrackerProps) {
  return (
    <div className="space-y-3">
      {stages.map((stage, i) => (
        <div
          key={stage.id}
          className={`stage-indicator ${stage.status}`}
        >
          {/* Icon */}
          <div className={`stage-icon ${stage.status}`}>
            {stage.status === "active" ? (
              <div className="spinner" style={{ width: 16, height: 16 }} />
            ) : stage.status === "completed" ? (
              "✓"
            ) : stage.status === "error" ? (
              "✕"
            ) : (
              stage.icon
            )}
          </div>

          {/* Content */}
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <span className={`font-medium ${stage.status === "pending" ? "text-white/40" : "text-white"}`}>
                {stage.name}
              </span>
              <span className="text-xs text-white/40">
                {stage.status === "completed" && "Done"}
                {stage.status === "active" && "In Progress..."}
                {stage.status === "error" && "Failed"}
              </span>
            </div>
            {stage.detail && (
              <div className="text-xs text-white/50 mt-1">{stage.detail}</div>
            )}
          </div>

          {/* Connector line */}
          {i < stages.length - 1 && (
            <div
              className={`absolute left-[31px] top-[52px] w-0.5 h-3 ${
                stage.status === "completed" ? "bg-green-500/50" : "bg-white/10"
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}
