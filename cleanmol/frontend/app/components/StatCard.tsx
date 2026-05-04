"use client";

interface StatCardProps {
  value: string | number;
  label: string;
  icon?: string;
}

export function StatCard({ value, label, icon }: StatCardProps) {
  return (
    <div className="stat-card">
      {icon && <div className="text-xs font-semibold tracking-widest text-cyan-300/80 mb-2">{icon}</div>}
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
