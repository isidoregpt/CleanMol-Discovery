export function LogConsole({ text }: { text: string }) {
  return (
    <pre className="rounded-xl bg-black/40 border border-white/10 p-4 text-xs font-mono overflow-auto max-h-80 whitespace-pre-wrap text-white/80">
      {text || "Waiting for pipeline run..."}
    </pre>
  );
}
