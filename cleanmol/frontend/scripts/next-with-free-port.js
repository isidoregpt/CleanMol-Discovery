const net = require("net");
const { spawn } = require("child_process");

const mode = process.argv[2] || "dev";
const preferredPort = Number.parseInt(
  process.env.CLEANMOL_FRONTEND_PORT || process.env.PORT || "3000",
  10
);
const maxAttempts = Number.parseInt(process.env.CLEANMOL_PORT_ATTEMPTS || "25", 10);

function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.unref();
    server.once("error", () => resolve(false));
    server.listen(port, () => {
      server.close(() => resolve(true));
    });
  });
}

async function findPort(startPort) {
  for (let offset = 0; offset < maxAttempts; offset += 1) {
    const port = startPort + offset;
    if (await isPortFree(port)) return port;
  }
  throw new Error(`No free frontend port found from ${startPort} to ${startPort + maxAttempts - 1}.`);
}

async function main() {
  const port = await findPort(Number.isFinite(preferredPort) ? preferredPort : 3000);
  if (port !== preferredPort) {
    console.log(`[CleanMol] Port ${preferredPort} is busy; using ${port} instead.`);
  }
  console.log(`[CleanMol] Starting Next.js ${mode} server on http://localhost:${port}`);

  if (process.env.CLEANMOL_FRONTEND_DRY_RUN === "1") {
    return;
  }

  const child = spawn("next", [mode, "-p", String(port)], {
    env: { ...process.env, PORT: String(port), CLEANMOL_FRONTEND_PORT: String(port) },
    shell: true,
    stdio: "inherit",
  });

  child.on("exit", (code, signal) => {
    if (signal) process.kill(process.pid, signal);
    process.exit(code ?? 0);
  });
}

main().catch((error) => {
  console.error(`[CleanMol] ${error.message}`);
  process.exit(1);
});
