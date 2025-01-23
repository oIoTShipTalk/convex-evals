from braintrust import Eval, init_logger, traced, current_span
from autoevals import LevenshteinScorer, Score
from runner.models.anthropic_codegen import AnthropicModel
from runner.models.openai_codegen import OpenAIModel
from runner.convex_backend import convex_backend, admin_key
import subprocess
import tempfile
import shutil
from dotenv import load_dotenv
import os

PROJECT = "Convex Coding"

load_dotenv()

logger = init_logger(project=PROJECT)

supported_models = ["gpt-4o", "claude-3-5-sonnet-latest", "o1", "o1-mini"]
max_concurrency = {
    "claude-3-5-sonnet-latest": 2,
    "gpt-4o": 4,
    "o1": 4,
    "o1-mini": 4,
}

if os.getenv("OUTPUT_TEMPDIR") is not None:

    tempdir = os.getenv("OUTPUT_TEMPDIR")
else:
    tempdir = tempfile.mkdtemp()
print(f"Using tempdir: {tempdir}")

def convex_coding_evals(model):
    assert model in supported_models, f"Model {model} not supported"

    eval_paths = [
        (category, name, f"evals/{category}/{name}")
        for category in os.listdir(f"evals")
        if os.path.isdir(f"evals/{category}")
        for name in os.listdir(f"evals/{category}")
        if os.path.isdir(f"evals/{category}/{name}")
    ]
    data = []
    for category, name, eval_path in eval_paths:
        with open(f"{eval_path}/TASK.txt", "r") as f:
            task_description = f.read()

        answer_paths = list(walk_answer(f"{eval_path}/answer"))
        answer_paths.sort(key=lambda x: (x.count("/"), x))

        expected = {}
        for file_path in answer_paths:
            with open(file_path, "r") as f:
                base_path = f"{eval_path}/answer"
                relative_path = os.path.relpath(file_path, base_path)
                file_content = f.read().strip()
                expected[relative_path] = file_content

        data.append({
            "input": task_description,
            "expected": expected,
            "metadata": {
                "category": category,
                "name": name,
                "model": model,
            }
        })

    return Eval(
        PROJECT,
        data=data,
        task=lambda input: convex_coding_task(model, input),
        scores=[lambda *args, **kwargs: convex_scorer(model, *args, **kwargs)],
        metadata={"model": model},
        max_concurrency=max_concurrency[model],
    )

def walk_answer(answer_dir):
    for dirpath, _, filenames in os.walk(answer_dir):
        if "node_modules" in dirpath or "_generated" in dirpath:
            continue
        for filename in filenames:
            if filename == "package.json" or filename.endswith(".ts"):
                yield os.path.join(dirpath, filename)

def convex_coding_task(model, input):
    if model.startswith("claude-3-5-sonnet"):
        model_impl = AnthropicModel(model)
    elif model.startswith("gpt") or model.startswith("o1"):
        model_impl = OpenAIModel(model)
    else:
        raise ValueError(f"Unknown model: {model}")
    return model_impl.generate(input)

def convex_scorer(model, *, args, expected, metadata, output):
    model = metadata['model']
    category = metadata['category']
    name = metadata['name']

    output_project_dir = f"{tempdir}/output/{model}/{category}/{name}"
    os.makedirs(output_project_dir, exist_ok=True)
    output_project_dir_abs = os.path.abspath(output_project_dir)

    scores = []

    try:
        write_filesystem(output_project_dir_abs, output)
        scores.append(Score("Valid filesystem output", 1))
    except Exception as e:
        scores.append(Score("Valid filesystem output", 0))
        return scores

    try:
        install_dependencies(output_project_dir_abs)
        scores.append(Score("`bun install` succeeds", 1))
    except Exception as e:
        scores.append(Score("`bun install` succeeds", 0))

    try:
        generate_code(output_project_dir_abs)
        scores.append(Score("`convex codegen` succeeds", 1))
    except Exception as e:
        scores.append(Score("`convex codegen` succeeds", 0))

    try:
        typecheck_code(output_project_dir_abs)
        scores.append(Score("Passes tsc", 1))
    except Exception as e:
        scores.append(Score("Passes tsc", 0))

    try:
        lint_code(output_project_dir_abs)
        scores.append(Score("Passes eslint", 1))
    except Exception as e:
        scores.append(Score("Passes eslint", 0))

    output_backend_dir = f"{tempdir}/backends/output/{model}/{category}/{name}"
    os.makedirs(output_backend_dir, exist_ok=True)

    with convex_backend(output_backend_dir) as output_backend:
        try:
            deploy(output_backend, output_project_dir_abs)
            scores.append(Score("`convex dev` succeeds", 1))
        except Exception as e:
            scores.append(Score("`convex dev` succeeds", 0))

        eval_path = f"evals/{category}/{name}"
        answer_project_dir, answer_backend_dir = setup_answer_backend(eval_path, model, category, name)
        install_dependencies(answer_project_dir)
        generate_code(answer_project_dir)

        with convex_backend(answer_backend_dir) as answer_backend:
            deploy(answer_backend, answer_project_dir)
            test_file = os.path.abspath(os.path.join(eval_path, "grader.test.ts"))
            try:
                run_tests(output_backend, answer_backend, test_file)
                scores.append(Score("Tests pass", 1))
            except Exception as e:
                scores.append(Score("Tests pass", 0))

    logger.flush()
    return scores

@traced
def write_filesystem(project_dir, output):
    project_dir_abs = os.path.abspath(project_dir)
    for relative_path, file_content in output.items():
        file_path = os.path.normpath(os.path.join(project_dir_abs, relative_path))
        if not file_path.startswith(project_dir_abs):
            raise Exception(f"Invalid filesystem output: {file_path} is not in {project_dir_abs}")

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(file_content)
@traced
def install_dependencies(project_dir):
    done = subprocess.run(
        ["bun", "install"],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    if done.returncode != 0:
        raise Exception(f"Failed to install dependencies:\n{done.stdout}")

@traced
def generate_code(project_dir):
    done = subprocess.run(
        ["bunx", "convex", "codegen", "--typecheck", "disable", "--init"],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    if done.returncode != 0:
        raise Exception(f"Failed to generate code:\n{done.stdout}")

@traced
def typecheck_code(project_dir):
    convex_dir = os.path.abspath(os.path.join(project_dir, "convex"))
    done = subprocess.run(
        ["bunx", "tsc", "-noEmit", "-p", convex_dir],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    if done.returncode != 0:
        raise Exception(f"Failed to typecheck code:\n{done.stdout}")


@traced
def lint_code(project_dir):
    eslint_config = os.path.abspath('eslint.config.mjs')
    done = subprocess.run(
        ["bunx", "eslint", "-c", eslint_config, 'convex'],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    if done.returncode != 0:
        raise Exception(f"Failed to lint code:\n{done.stdout}")

@traced
def deploy(backend, project_dir):
    done = subprocess.run(
        [
            "bunx",
            "convex",
            "dev",
            "--once",
            "--admin-key",
            admin_key,
            "--url",
            f"http://localhost:{backend['port']}",
        ],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    if done.returncode != 0:
        raise Exception(f"Failed to deploy:\n{done.stdout}")

@traced
def setup_answer_backend(eval_path, model, category, name):
    answer_project_dir = f"{tempdir}/answer/{model}/{category}/{name}"
    os.makedirs(answer_project_dir, exist_ok=True)

    answer_dir = f"{eval_path}/answer"

    for source_path in walk_answer(answer_dir):
        relative_path = os.path.relpath(source_path, answer_dir)
        destination_path = os.path.join(answer_project_dir, relative_path)
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        shutil.copy(source_path, destination_path)

    answer_backend_dir = f"{tempdir}/backends/answer/{model}/{category}/{name}"
    os.makedirs(answer_backend_dir, exist_ok=True)

    return answer_project_dir, answer_backend_dir

@traced
def run_tests(backend, answer_backend, test_file):
    env = dict(
        os.environ,
        CONVEX_PORT=str(backend["port"]),
        CONVEX_ANSWER_PORT=str(answer_backend["port"]),
    )
    done = subprocess.run(
        [
            "bunx",
            "vitest",
            "run",
            test_file,
            "--no-color",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    if done.returncode != 0:
        raise Exception(f"Failed to run tests:\n{done.stdout}")

convex_coding_evals("claude-3-5-sonnet-latest")
