import "./globals.css";

export const metadata = {
  title: "Kevin — Dataset Builder",
  description: "Multi-model AI pipeline for chemistry dataset mining"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
