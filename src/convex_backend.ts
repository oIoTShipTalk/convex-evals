import { join } from "path";
import { spawn, spawnSync } from "child_process";
import { mkdir, open } from "fs/promises";

async function healthCheck() {
  const deadline = Date.now() + 10000;
  let numAttempts = 0;

  while (true) {
    try {
      const response = await fetch("http://localhost:3210/version");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return true;
    } catch (e) {
      const remaining = deadline - Date.now();
      if (remaining < 0) throw e;

      await new Promise((resolve) =>
        setTimeout(resolve, Math.min(100 * Math.pow(2, numAttempts), remaining))
      );
      numAttempts++;
    }
  }
}

export async function deploy(outputDir: string) {
  const projectDir = join(outputDir, "project");
  const backendDir = join(outputDir, "backend");
  await mkdir(backendDir, { recursive: true });

  const storageDir = join(backendDir, "convex_local_storage");
  await mkdir(storageDir, { recursive: true });

  const sqlitePath = join(backendDir, "convex_local_backend.sqlite3");
  const instanceName = "carnitas";
  const instanceSecret =
    "4361726e697461732c206c69746572616c6c79206d65616e696e6720226c6974";
  const adminKey =
    "0135d8598650f8f5cb0f30c34ec2e2bb62793bc28717c8eb6fb577996d50be5f4281b59181095065c5d0f86a2c31ddbe9b597ec62b47ded69782cd";
  const convexBinary = join(process.cwd(), "convex-local-backend");

  const stdoutFile = await open(join(backendDir, "backend.stdout.log"), "w");
  const stderrFile = await open(join(backendDir, "backend.stderr.log"), "w");

  const convexProcess = spawn(
    convexBinary,
    [
      "--port",
      "3210",
      "--site-proxy-port",
      "3211",
      "--instance-name",
      instanceName,
      "--instance-secret",
      instanceSecret,
      "--local-storage",
      storageDir,
      sqlitePath,
    ],
    {
      cwd: backendDir,
      stdio: ["ignore", stdoutFile.fd, stderrFile.fd],
    }
  );

  try {
    await healthCheck();

    if (convexProcess.exitCode !== null)
      throw new Error("Convex process failed to start");

    const result = spawnSync(
      "bunx",
      [
        "convex",
        "dev",
        "--once",
        "--admin-key",
        adminKey,
        "--url",
        "http://localhost:3210",
      ],
      {
        cwd: projectDir,
        stdio: "inherit",
      }
    );

    if (result.status !== 0)
      throw new Error(`Deploy failed with code ${result.status}`);

    console.log("Deploy OK!");
  } finally {
    convexProcess.kill();
    await stdoutFile.close();
    await stderrFile.close();
  }
}
