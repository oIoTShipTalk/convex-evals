import { join } from "path";
import { spawn } from "child_process";
import { VerificationError } from "./errors.js";

export async function setupJs(outputDir: string) {
  const projectDir = join(outputDir, "project");

  await new Promise<void>((resolve, reject) => {
    const proc = spawn("bun", ["install"], {
      cwd: projectDir,
      stdio: "inherit",
    });

    proc.on("close", (code) => {
      if (code === 0) {
        console.log("Install OK!");
        resolve();
      } else reject(new Error(`Install failed with code ${code}`));
    });
  });

  await new Promise<void>((resolve, reject) => {
    const proc = spawn(
      "bunx",
      ["convex", "codegen", "--typecheck", "disable", "--init"],
      {
        cwd: projectDir,
        stdio: "inherit",
      }
    );

    proc.on("close", (code) => {
      if (code === 0) {
        console.log("Codegen OK!");
        resolve();
      } else reject(new Error(`Codegen failed with code ${code}`));
    });
  });
}

export async function typecheckJs(outputDir: string) {
  const convexDir = join(outputDir, "project", "convex");

  const output = await new Promise<string>((resolve, reject) => {
    let stdout = "";
    const proc = spawn("bunx", ["tsc", "-noEmit", "-p", convexDir], {
      stdio: ["ignore", "pipe", "pipe"],
    });

    proc.stdout.on("data", (data) => (stdout += data));
    proc.stderr.on("data", (data) => (stdout += data));

    proc.on("close", (code) => {
      if (code === 0) {
        console.log("Typecheck OK!");
        resolve(stdout);
      } else
        reject(
          new VerificationError("Typechecking failed", stdout.split("\n"))
        );
    });
  });
}

export async function lintJs(outputDir: string) {
  const convexDir = join(outputDir, "project", "convex");

  const output = await new Promise<string>((resolve, reject) => {
    let stdout = "";
    const proc = spawn(
      "bunx",
      ["eslint", "-c", "eslint.config.mjs", convexDir],
      {
        stdio: ["ignore", "pipe", "pipe"],
      }
    );

    proc.stdout.on("data", (data) => (stdout += data));
    proc.stderr.on("data", (data) => (stdout += data));

    proc.on("close", (code) => {
      if (code === 0) {
        console.log("ESLint OK!");
        resolve(stdout);
      } else {
        try {
          const errors = JSON.parse(stdout);
          for (const error of errors) delete error.source;
          reject(new VerificationError("Linting failed", errors));
        } catch {
          reject(new Error(`ESLint failed with output: ${stdout}`));
        }
      }
    });
  });
}
