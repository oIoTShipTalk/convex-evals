import os
import sys
import subprocess

category = sys.argv[1]
name = sys.argv[2]

evals_dir = "evals"
categories = os.listdir(evals_dir)

category_by_name = {category.split("-")[1]: category for category in categories}
next_category_number = max(int(category.split("-")[0]) for category in categories) + 1

if category not in category_by_name:
    print(f"Creating new category {category}")
    category_dir = os.path.join(evals_dir, f"{next_category_number:03d}-{category}")
    os.makedirs(category_dir)
else:
    category_dir = os.path.join(evals_dir, category_by_name[category])

existing = [int(existing_name.split("-")[0]) for existing_name in os.listdir(category_dir)]

if existing:
    next_id = max(existing) + 1
else:
    next_id = 0

assert "-" not in name
testdir_name = f"{next_id:03d}-{name}"

testdir = os.path.join(category_dir, testdir_name)
os.makedirs(testdir)

with open(os.path.join(testdir, "TASK.txt"), "w") as f:
    f.write(f"Create a backend for a {name} system.")

answer_dir = os.path.join(testdir, "answer")
os.makedirs(answer_dir)

package_json = """{
  "name": "convexbot",
  "version": "1.0.0",
  "dependencies": {
    "convex": "^1.17.4"
  }
}""".strip()

with open(os.path.join(answer_dir, "package.json"), "w") as f:
    f.write(package_json)

convex_dir = os.path.join(answer_dir, "convex")
os.makedirs(convex_dir)

with open(os.path.join(convex_dir, "index.ts"), "w") as f:
    f.write('import { v } from "convex/values"\n')
    f.write('import { query } from "./_generated/server"\n')

grader_ts = """
import { expect, test } from "vitest";
import { adminClient, client, compareSchema, compareFunctionSpec } from "../../../grader";
import { anyApi } from "convex/server"

test("compare schema", async ({ skip }) => {
  await compareSchema(skip);
})

test("compare function spec", async ({ skip }) => {
  await compareFunctionSpec(skip);
})
"""

with open(os.path.join(testdir, "grader.test.ts"), "w") as f:
    f.write(grader_ts)

subprocess.run(["bun", "install"], cwd=answer_dir, check=True)
subprocess.run(["bunx", "convex", "codegen"], cwd=answer_dir, check=True)
