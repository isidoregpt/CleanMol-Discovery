export function Button({
  children,
  onClick,
  disabled,
  variant = "primary"
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "success";
}) {
  const baseClass = "rounded-xl px-5 py-3 font-semibold transition active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed";
  const variantClasses = {
    primary: "bg-white text-black hover:bg-white/90",
    secondary: "bg-white/10 hover:bg-white/15 border border-white/10",
    success: "bg-emerald-500 text-black hover:bg-emerald-400"
  };

  return (
    <button
      className={`${baseClass} ${variantClasses[variant]}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}
