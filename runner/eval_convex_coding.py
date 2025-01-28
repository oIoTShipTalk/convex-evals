from braintrust import Eval, init_logger
from runner.models.anthropic_codegen import AnthropicModel
from runner.models.openai_codegen import OpenAIModel
from runner.scorer import convex_scorer, walk_answer
import tempfile
from dotenv import load_dotenv
import os
import re

PROJECT = "Convex Coding"

load_dotenv()

logger = init_logger(project=PROJECT)

supported_models = ["gpt-4o", "claude-3-5-sonnet-latest", "o1", "o1-mini", "deepseek-ai/DeepSeek-R1"]
anthropic_concurrency = int(os.getenv("ANTHROPIC_CONCURRENCY", "2"))
openai_concurrency = int(os.getenv("OPENAI_CONCURRENCY", "4"))
max_concurrency = {
    "claude-3-5-sonnet-latest": anthropic_concurrency,
    "gpt-4o": openai_concurrency,
    "o1": openai_concurrency,
    "o1-mini": openai_concurrency,
    "deepseek-ai/DeepSeek-V3": openai_concurrency,
    "deepseek-ai/DeepSeek-R1": openai_concurrency,
}

if os.getenv("OUTPUT_TEMPDIR") is not None:
    tempdir = os.getenv("OUTPUT_TEMPDIR")
else:
    tempdir = tempfile.mkdtemp()
print(f"Using tempdir: {tempdir}")

test_filter = None
if os.getenv("TEST_FILTER") is not None:
    test_filter = re.compile(os.getenv("TEST_FILTER"))


def convex_coding_evals(model):
    assert model in supported_models, f"Model {model} not supported"

    eval_paths = [
        (category, name, f"evals/{category}/{name}")
        for category in os.listdir("evals")
        if os.path.isdir(f"evals/{category}")
        for name in os.listdir(f"evals/{category}")
        if os.path.isdir(f"evals/{category}/{name}")
    ]
    data = []
    for category, name, eval_path in eval_paths:
        if test_filter is not None and not test_filter.search(f"{category}/{name}"):
            continue

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

        data.append(
            {
                "input": task_description,
                "expected": expected,
                "metadata": {
                    "category": category,
                    "name": name,
                    "model": model,
                },
            }
        )

    return Eval(
        PROJECT,
        data=data,
        task=lambda input: convex_coding_task(model, input),
        scores=[lambda *args, **kwargs: convex_scorer(model, tempdir, *args, **kwargs)],
        metadata={
            "model": model,
            "tempdir": tempdir,
        },
        max_concurrency=max_concurrency[model],
    )


def convex_coding_task(model, input):
    if model.startswith("claude-3-5-sonnet"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        model_impl = AnthropicModel(api_key, model)
    elif model.startswith("gpt") or model.startswith("o1"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        model_impl = OpenAIModel(api_key, model)
    elif model.startswith("deepseek-ai"):
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            raise ValueError("TOGETHER_API_KEY is not set")
        model_impl = OpenAIModel(api_key, model)
    else:
        raise ValueError(f"Unknown model: {model}")
    return model_impl.generate(input)


convex_coding_evals("claude-3-5-sonnet-latest")
# convex_coding_evals("gpt-4o")
# convex_coding_evals("o1")
# convex_coding_evals("o1-mini")
# convex_coding_evals("deepseek-ai/DeepSeek-R1")
