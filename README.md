# Convex Coding Evals

LLMs don't have _perfect_ knowledge of Convex, so they require some prompting
to help them along. This repo contains a set of prompts for coding a Convex
backend, a set of human-curated solutions, and a script for evaluating the
LLM's output.

## Running the evaluations

```bash
pip install pdm
pdm install

npm install -g bun
bun install

echo "ANTHROPIC_API_KEY=<your ANTHROPIC_API_KEY>" > .env
echo "OPENAI_API_KEY=<your OPENAI_API_KEY>" >> .env

pdm run python runner/main.py --model=claude-3-5-sonnet-latest --generate-concurrency=1
```

You can also specify a test filter regex:
```bash
pdm run python runner/main.py --model=claude-3-5-sonnet-latest --generate-concurrency=1 --test-filter='.*data_modeling.*'
```

If you'd like to grade the evaluations again without regenerating them, run:

```bash
pdm run python runner/main.py --skip-generation
```

Here is the Next app for viewing the report:

```bash
cd viewer
bun install
bun dev
```

## Creating a new evaluation

```bash
pdm run python create_eval.py <name> <category>
```

For example, adding a new fundmentals eval for using HTTP actions and storage would be:

```bash
pdm run python create_eval.py http_actions_file_storage 000-fundamentals
```

Note that test or category names cannot contain dashes.

# Outstanding Evals

+ [ordering](https://docs.convex.dev/database/reading-data#ordering)