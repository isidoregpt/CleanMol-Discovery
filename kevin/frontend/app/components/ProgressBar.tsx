"use client";

import { useEffect, useState } from "react";

interface ProgressBarProps {
  progress: number; // 0-100
  stage: string;
  isActive: boolean;
}

export function ProgressBar({ progress, stage, isActive }: ProgressBarProps) {
  const [particles, setParticles] = useState<number[]>([]);

  useEffect(() => {
    if (isActive) {
      // Generate particles
      const interval = setInterval(() => {
        setParticles(prev => {
          const newParticles = [...prev, Date.now()];
          // Keep only last 20 particles
          return newParticles.slice(-20);
        });
      }, 200);
      return () => clearInterval(interval);
    }
  }, [isActive]);

  return (
    <div className="space-y-3">
      {/* Stage label */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          {isActive && (
            <div className="live-indicator">
              <span className="live-dot" />
              <span>Processing</span>
            </div>
          )}
          <span className="text-sm font-medium text-white/80">{stage}</span>
        </div>
        <span className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-fuchsia-400 bg-clip-text text-transparent">
          {progress}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="progress-container">
        {/* Particles */}
        <div className="progress-particles">
          {isActive && particles.map((id, i) => (
            <span
              key={id}
              className="particle"
              style={{
                left: `${Math.min(progress, 95)}%`,
                animationDelay: `${i * 0.1}s`,
                transform: `translateX(${Math.random() * 20 - 10}px)`,
              }}
            />
          ))}
        </div>

        {/* Progress fill */}
        <div
          className="progress-bar"
          style={{ width: `${progress}%` }}
        />

        {/* Percentage inside bar */}
        {progress > 15 && (
          <div
            className="absolute inset-y-0 flex items-center pl-4 text-black font-bold text-sm"
            style={{ width: `${progress}%` }}
          >
            {stage}
          </div>
        )}
      </div>
    </div>
  );
}
