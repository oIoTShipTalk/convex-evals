import os
import sys
import subprocess
from runner.models.anthropic_codegen import AnthropicModel
import glob
from dotenv import load_dotenv
from .convex_backend import convex_backend, admin_key

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY is not set")
model = AnthropicModel(str(api_key), "claude-3-5-sonnet-latest")

output_tempdir = os.getenv("OUTPUT_TEMPDIR")
if not output_tempdir:
    output_tempdir = "/tmp/convex-codegen-evals"

def input_continue(message="Press enter to continue..."):
    input(message)


def open_in_cursor(filepath):
    subprocess.run(["cursor", filepath], check=False)
    input_continue(f"Opened {filepath} in Cursor. Press enter when done editing...")


def get_example_tasks():
    tasks = []
    for task_file in glob.glob("evals/**/TASK.txt", recursive=True):
        with open(task_file, "r") as f:
            tasks.append(f.read().strip())
    return tasks

def get_answer_convex_files(eval_dir):
    files = {}
    answer_dir = os.path.join(eval_dir, "answer")
    convex_dir = os.path.join(answer_dir, "convex")
    for filename in os.listdir(convex_dir):
        if filename.endswith(".ts"):
            file_path = os.path.join(convex_dir, filename)
            rel_path = os.path.relpath(file_path, answer_dir)
            with open(file_path, "r") as f:
                files[rel_path] = f.read().strip()
    return files

def get_example_evals(before_dir, n=5):
    """Get the latest evals with their task, files and grader test"""
    evals = []
    for task_file in sorted(glob.glob("evals/**/TASK.txt", recursive=True), reverse=True):
        if task_file > before_dir:
            continue
        eval_dir = os.path.dirname(task_file)

        # Read task
        with open(task_file, "r") as f:
            task = f.read().strip()

        # Get all files in answer/convex
        files = get_answer_convex_files(eval_dir)
        # Read grader test
        grader_file = os.path.join(eval_dir, "grader.test.ts")
        if os.path.exists(grader_file):
            with open(grader_file, "r") as f:
                grader_test = f.read().strip()

            evals.append({"task": task, "files": files, "grader_test": grader_test})

            if len(evals) >= n:
                break

    return evals


def generate_task_description(one_line_desc, example_tasks):
    prompt = f"""Given this one line description of a task:
{one_line_desc}

Please generate a detailed TASK.txt file describing what needs to be implemented. The task should be clear and specific about what Convex backend files and functions need to be created.

Here are some example TASK.txt files for reference:

{chr(10).join(f'=== EXAMPLE {i+1} ==={chr(10)}{task}{chr(10)}' for i, task in enumerate(example_tasks[-10:]))}
=== END EXAMPLES ===

Generate a similar style TASK.txt for the given one-line description:
{one_line_desc}"""

    primer = "Create a backend that"
    response = model.client.chat.completions.create(
        model="claude-3-5-sonnet-latest",
        messages=[{"role": "user", "content": prompt}, {"role": "assistant", "content": primer}],
        max_tokens=1000,
    )
    return primer + " " + response.choices[0].message.content.strip()


def generate_task_test(task, files, examples):

    def format_prompt(task, files):
        return f"""Given a task description and implementation files, generate a grader.test.ts file to test the implementation.

The test file should:
1. Import the necessary test utilities
2. Always include the schema and function spec comparison tests
3. Add specific tests to verify the implementation works as expected

Current task:
{task}

Implementation files:
{chr(10).join(f'=== {path} ==={chr(10)}{content}' for path, content in files.items())}

Generate vitest test file contents for the current task."""

    example_messages = [
        [{"role": "user", "content": format_prompt(example["task"], example["files"])}, {"role": "assistant", "content": example["grader_test"]}]
        for example in examples
    ]
    response = model.client.chat.completions.create(
        model="claude-3-5-sonnet-latest",
        messages=[
            *[message for example in example_messages for message in example],
            {"role": "user", "content": format_prompt(task, files)},
        ],
        max_tokens=2000,
    )
    return response.choices[0].message.content.strip()


def main():
    # Parse args
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python create_eval.py <category> <name> [start_step]")
        sys.exit(1)

    category = sys.argv[1]
    name = sys.argv[2]
    start_step = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    def should_run_step(step_num):
        return step_num >= start_step

    evals_dir = "evals"
    categories = os.listdir(evals_dir)

    category_by_name = {category.split("-")[1]: category for category in categories}
    next_category_number = max(int(category.split("-")[0]) for category in categories) + 1

    new_category = category not in category_by_name
    if new_category:
        print(f"Creating new category {category}")
        category_dir = os.path.join(evals_dir, f"{next_category_number:03d}-{category}")
    else:
        category_dir = os.path.join(evals_dir, category_by_name[category])

    print(f"\nStep 1: Creating eval directory for category '{category}' and name '{name}'")
    if should_run_step(1):
        os.makedirs(category_dir, exist_ok=True)

    existing_by_name = {name.split("-")[1]: name for name in os.listdir(category_dir)}

    assert "-" not in name
    if name in existing_by_name:
        testdir_name = existing_by_name[name]
    else:
        existing = [int(existing_name.split("-")[0]) for existing_name in os.listdir(category_dir)]
        next_id = max(existing) + 1 if existing else 0
        testdir_name = f"{next_id:03d}-{name}"
    testdir = os.path.join(category_dir, testdir_name)
    if should_run_step(1):
        os.makedirs(testdir, exist_ok=True)

    task_file = os.path.join(testdir, "TASK.txt")
    print("\nStep 2: Generate TASK.txt with a one-line description")
    if should_run_step(2):
        one_line_desc = input("Description: ")

        example_tasks = get_example_tasks()
        task_description = generate_task_description(one_line_desc, example_tasks)
        with open(task_file, "w") as f:
            f.write(task_description)
        open_in_cursor(task_file)

    print("\nStep 3: Creating answer directory and package.json")
    answer_dir = os.path.join(testdir, "answer")
    convex_dir = os.path.join(answer_dir, "convex")
    if should_run_step(3):
        os.makedirs(answer_dir, exist_ok=True)
        os.makedirs(convex_dir, exist_ok=True)

        package_json = """{
  "name": "convexbot",
  "version": "1.0.0",
  "dependencies": {
    "convex": "^1.17.4"
  }
}""".strip()

        with open(os.path.join(answer_dir, "package.json"), "w") as f:
            f.write(package_json)

        # Run bun install and codegen
        subprocess.run(["bun", "install"], cwd=answer_dir, check=True)
        subprocess.run(["bunx", "convex", "codegen"], cwd=answer_dir, check=True)

    print("\nStep 4: Generating answer/convex files and editing index.ts")
    if should_run_step(4):
        with open(task_file, "r") as f:
            task_content = f.read()

        generated_files = model.generate(task_content)
        for path, content in generated_files.items():
            full_path = os.path.join(answer_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
        # Re-run codegen to generate the _generated files for the schema
        subprocess.run(["bunx", "convex", "codegen"], cwd=answer_dir, check=False)
        open_in_cursor(os.path.join(convex_dir, "index.ts"))

    print("\nStep 5: Generating grader.test.ts")
    grader_file = os.path.join(testdir, "grader.test.ts")
    if should_run_step(5):
        # Get implementation files
        files = get_answer_convex_files(testdir)

        # Get task description
        with open(task_file, "r") as f:
            task_content = f.read().strip()

        # Get example evals (before the current testdir)
        examples = get_example_evals(testdir)

        # Generate test file
        grader_test = generate_task_test(task_content, files, examples)

        with open(grader_file, "w") as f:
            f.write(grader_test)

        print("\nOpening grader.test.ts for editing")
        open_in_cursor(grader_file)

    env = os.environ.copy()
    print("\nStep 6: Running tests interactively")
    if should_run_step(6):
        backend_dir = os.path.join(testdir, "backend")
        with convex_backend(backend_dir) as backend:
            convex_dev_process = subprocess.Popen(
                [
                    "bunx",
                    "convex",
                    "dev",
                    "--admin-key",
                    admin_key,
                    "--url",
                    f"http://localhost:{backend['port']}",
                ],
                cwd=answer_dir,
                stdout=sys.stdout,
                stderr=sys.stderr,
                encoding="utf-8",
            )

            # copy env and add CONVEX_PORT
            env = os.environ.copy()
            env["CONVEX_PORT"] = str(backend["port"])

            subprocess.run(
                [
                    "bunx",
                    "vitest",
                    grader_file,
                    # "--no-color",
                ],
                env=env,
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
                encoding="utf-8",
                check=False,
            )
            convex_dev_process.kill()

    print("\nStep 7: Running eval and reporting gaps")
    if should_run_step(7):
        test_filter = f"{category}/{testdir_name}"
        env["TEST_FILTER"] = test_filter
        env["OUTPUT_TEMPDIR"] = output_tempdir

        subprocess.run(
            ["pdm", "run", "braintrust", "eval", "runner/eval_convex_coding.py"],
            env=env,
            check=False,
        )

        gaps_file = os.path.join(testdir, "GAPS.txt")
        with open(gaps_file, "w") as f:
            f.write(f"{category}, {name}:\n")
        open_in_cursor(gaps_file)

    print("\nStep 8: Committing to git")
    if should_run_step(8):
        subprocess.run(["git", "add", testdir], check=True)
        subprocess.run(["git", "commit", "-m", f"eval: {category} {name}"], check=True)

    print("\nDone! New eval created at:", testdir)


if __name__ == "__main__":
    main()
