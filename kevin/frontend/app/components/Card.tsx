export function Card({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl bg-white/5 border border-white/10 shadow-[0_0_0_1px_rgba(255,255,255,.06),0_20px_80px_rgba(0,0,0,.65)] backdrop-blur-xl">
      {title && (
        <div className="px-6 py-4 border-b border-white/10">
          <h2 className="text-lg font-semibold">{title}</h2>
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  );
}
