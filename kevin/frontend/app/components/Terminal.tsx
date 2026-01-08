"use client";

import { useEffect, useRef } from "react";

export interface TerminalLine {
  timestamp: string;
  type: "info" | "success" | "error" | "warning" | "system" | "dim";
  prefix?: string;
  text: string;
}

interface TerminalProps {
  lines: TerminalLine[];
  isRunning: boolean;
  title?: string;
}

export function Terminal({ lines, isRunning, title = "Pipeline Output" }: TerminalProps) {
  const bodyRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [lines]);

  return (
    <div className="terminal">
      {/* Header */}
      <div className="terminal-header">
        <span className="terminal-dot red" />
        <span className="terminal-dot yellow" />
        <span className="terminal-dot green" />
        <span className="terminal-title">{title}</span>
        {isRunning && <div className="spinner" />}
      </div>

      {/* Body */}
      <div ref={bodyRef} className="terminal-body">
        {lines.length === 0 ? (
          <div className="terminal-line">
            <span className="terminal-text dim">
              Awaiting pipeline execution...
            </span>
            <span className="terminal-cursor" />
          </div>
        ) : (
          <>
            {lines.map((line, i) => (
              <div key={i} className="terminal-line fade-in">
                <span className="terminal-timestamp">{line.timestamp}</span>
                {line.prefix && (
                  <span className="terminal-prefix">[{line.prefix}]</span>
                )}
                <span className={`terminal-text ${line.type}`}>
                  {line.text}
                </span>
              </div>
            ))}
            {isRunning && (
              <div className="terminal-line">
                <span className="terminal-timestamp"></span>
                <span className="terminal-cursor" />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
