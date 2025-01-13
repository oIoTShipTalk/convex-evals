import { config } from "dotenv";
import { program } from "commander";
import { Anthropic } from "@anthropic-ai/sdk";
import { execSync } from "child_process";
import { mkdir, access } from "fs/promises";
import { join } from "path";
import { generateTest } from "./generate.js";
import { setupJs, lintJs, typecheckJs } from "./typescript.js";
import { deploy } from "./convex_backend.js";
import { readdirSync, rmSync } from "fs";

config();

interface ReportEntry {
  category: string;
  test: string;
  setup?: { status: string; error?: string };
  typecheck?: { status: string; error?: string };
  lint?: { status: string; error?: string };
  deploy?: { status: string; error?: string };
}

async function main() {
  program
    .option("-f, --force", "Overwrite output directory if it exists")
    .option("--evals-dir <dir>", "Evals directory", "evals")
    .option("--output-dir <dir>", "Output directory")
    .option("-k, --test-filter <regexp>", "Filter tests by regexp")
    .option("-g, --skip-generation", "Skip generation")
    .option("-e, --skip-evaluation", "Skip evaluation")
    .option("-c, --concurrency <number>", "Concurrency", "4")
    .option("--report <path>", "Path for writing report JSON file")
    .parse();

  const options = program.opts();

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error("ANTHROPIC_API_KEY is not set");

  const client = new Anthropic({ apiKey });

  const doGeneration = !options.skipGeneration;
  const doEvaluation = !options.skipEvaluation;
  const evalsDir = options.evalsDir;
  let outputDir = options.outputDir;

  if (!outputDir) {
    const gitRev = execSync("git rev-parse HEAD").toString().trim();
    outputDir = `output-${gitRev}`;
  }

  const concurrency = parseInt(options.concurrency);
  const reportPath = options.report;

  const testFilter = options.testFilter ? new RegExp(options.testFilter) : null;

  const tests = readdirSync(evalsDir)
    .filter((category) => {
      try {
        return readdirSync(join(evalsDir, category))
          .filter((test) => {
            const testPath = join(evalsDir, category, test);
            return !testFilter || testFilter.test(test);
          })
          .map((test) => [category, test] as [string, string]);
      } catch {
        return [];
      }
    })
    .flat()
    .sort();

  if (doGeneration) {
    if (options.force) {
      try {
        rmSync(outputDir, { recursive: true });
      } catch {}
    }

    await mkdir(outputDir, { recursive: true });

    const promises = tests.map(async ([category, test]) => {
      const testDir = join(evalsDir, category, test);
      console.log(`Generating ${testDir}...`);
      try {
        await generateTest({
          inputDir: testDir,
          outputRoot: outputDir,
          client,
        });
      } catch (e) {
        console.error(`Error generating ${testDir}: ${e}`);
        throw e;
      }
    });

    try {
      await Promise.all(promises);
    } catch {
      throw new Error("Generation failed.");
    }
  }

  if (doEvaluation) {
    let anyFailed = false;
    const report: ReportEntry[] = [];

    for (const [category, test] of tests) {
      console.log(`Evaluating ${category}/${test}...`);
      const testOutputDir = join(outputDir, "evals", category, test);

      const reportEntry: ReportEntry = {
        category,
        test,
      };

      let allOk = true;

      try {
        await setupJs(testOutputDir);
        reportEntry.setup = { status: "ok" };
      } catch (e) {
        reportEntry.setup = { status: "failed", error: String(e) };
        allOk = false;
      }

      if (reportEntry.setup?.status === "ok") {
        try {
          await typecheckJs(testOutputDir);
          reportEntry.typecheck = { status: "ok" };
        } catch (e) {
          reportEntry.typecheck = { status: "failed", error: String(e) };
          allOk = false;
        }

        try {
          await lintJs(testOutputDir);
          reportEntry.lint = { status: "ok" };
        } catch (e) {
          reportEntry.lint = { status: "failed", error: String(e) };
          allOk = false;
        }

        try {
          await deploy(testOutputDir);
          reportEntry.deploy = { status: "ok" };
        } catch (e) {
          reportEntry.deploy = { status: "failed", error: String(e) };
          allOk = false;
        }
      }

      report.push(reportEntry);
      if (!allOk) anyFailed = true;
    }

    if (reportPath)
      await Bun.write(reportPath, JSON.stringify(report, null, 2));

    if (anyFailed) throw new Error("Evaluation failed.");
  }
}

main().catch(console.error);
