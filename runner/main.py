import os
import re
import json
import sys
import time
import requests
from anthropic import Anthropic
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import subprocess
from convex_backend import deploy, convex_backend, run_tests
from generate import generate
from typescript import setup_js, lint_js, typecheck_js
import argparse
import concurrent.futures
from errors import error_status
from models.anthropic_codegen import AnthropicModel
from models.openai_codegen import OpenAIModel
from models import ConvexCodegenModel


def generate_test(input_dir: str, output_root: str, model: ConvexCodegenModel):
    output_dir = os.path.join(output_root, input_dir)
    os.makedirs(output_dir, exist_ok=True)
    generate(input_dir, output_dir, model)


def evaluate_test(evals_dir: str, category: str, test: str, test_output_dir: str):
    test_dir = os.path.join(evals_dir, category, test)
    report_entry = {
        "category": category,
        "test": test,
        "setup": {"status": "skipped"},
        "typecheck": {"status": "skipped"},
        "lint": {"status": "skipped"},
        "deploy": {"status": "skipped"},
        "tests": {"status": "skipped"},
    }

    try:
        setup_js(test_output_dir)
        report_entry["setup"] = {"status": "ok"}
    except Exception as e:
        print(f"Error setting up: {e}")
        report_entry["setup"] = {"status": "failed", "error": str(e)}
        return report_entry, False

    try:
        typecheck_js(test_output_dir)
        report_entry["typecheck"] = {"status": "ok"}
    except Exception as e:
        print(f"Error typechecking: {e}")
        report_entry["typecheck"] = error_status(e)

    try:
        lint_js(test_output_dir)
        report_entry["lint"] = {"status": "ok"}
    except Exception as e:
        print(f"Error linting: {e}")
        report_entry["lint"] = error_status(e)

    backend_dir = os.path.join(test_output_dir, "backend")
    os.makedirs(backend_dir, exist_ok=True)

    answer_backend_dir = os.path.join(test_dir, "backend")
    os.makedirs(answer_backend_dir, exist_ok=True)

    with convex_backend(backend_dir) as backend:
        project_dir = os.path.join(test_output_dir, "project")
        try:
            deploy(backend, project_dir)
            report_entry["deploy"] = {"status": "ok"}
        except Exception as e:
            print(f"Error deploying: {e}")
            report_entry["deploy"] = error_status(e)
            return report_entry, False

        with convex_backend(answer_backend_dir) as answer_backend:
            answer_dir = os.path.join(test_dir, "answer")
            deploy(answer_backend, answer_dir)

            test_file = os.path.abspath(os.path.join(test_dir, "grader.test.ts"))
            if os.path.exists(test_file):
                try:
                    run_tests(backend, answer_backend, test_file)
                    report_entry["tests"] = {"status": "ok"}
                except Exception as e:
                    print(f"Error running tests: {e}")
                    report_entry["tests"] = error_status(e)

    all_ok = all(v["status"] != "error" for k, v in report_entry.items() if "status" in v)
    return report_entry, all_ok


if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run tests with specified input and output directories"
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite output directory if it exists"
    )
    parser.add_argument("--evals-dir", help="Evals directory", default="evals")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--test-filter", "-k", help="Filter tests by regexp")
    parser.add_argument("--skip-generation", "-g", action="store_true", help="Skip generation")
    parser.add_argument("--skip-evaluation", "-e", action="store_true", help="Skip evaluation")
    parser.add_argument("--generate-concurrency", help="Concurrency", default=4)
    parser.add_argument("--evaluate-concurrency", help="Concurrency", default=8)
    parser.add_argument(
        "--model", help="Model to use for generation", default="claude-3-5-sonnet-latest"
    )

    args = parser.parse_args()

    do_generation = not args.skip_generation
    do_evaluation = not args.skip_evaluation

    model = None
    if do_generation:
        if args.model.startswith("claude-3-5-sonnet"):
            model = AnthropicModel(args.model)
        elif args.model.startswith("gpt") or args.model.startswith("o1"):
            model = OpenAIModel(args.model)
        else:
            raise ValueError(f"Unknown model: {args.model}")

    evals_dir = args.evals_dir
    output_dir = args.output_dir
    if not output_dir:
        git_rev = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
        output_dir = f"output-{args.model}-{git_rev}"

    if os.path.exists(output_dir) and not args.force:
        response = input(f"Output directory '{output_dir}' already exists. Would you like to replace it? [y/N] ").strip()
        if not response or response.lower() != 'y':
            print("Aborting...")
            sys.exit(1)
        import shutil
        shutil.rmtree(output_dir)
        
    generate_concurrency = int(args.generate_concurrency)
    evaluate_concurrency = int(args.evaluate_concurrency)
    report_path = os.path.join(output_dir, "report.json")

    test_filter = re.compile(args.test_filter) if args.test_filter else None
    tests = [
        (category, test)
        for category in os.listdir(evals_dir)
        if os.path.isdir(os.path.join(evals_dir, category))
        for test in os.listdir(os.path.join(evals_dir, category))
        if os.path.isdir(os.path.join(evals_dir, category, test))
        if test_filter is None or test_filter.match(f"{category}/{test}")
    ]
    tests.sort()

    if do_generation:
        os.makedirs(output_dir, exist_ok=args.force)

        with concurrent.futures.ThreadPoolExecutor(max_workers=generate_concurrency) as executor:
            futures = {}
            for category, test in tests:
                test_dir = os.path.join(evals_dir, category, test)
                future = executor.submit(generate_test, test_dir, output_dir, model)
                futures[future] = (category, test_dir)
            any_failed = False
            for future in concurrent.futures.as_completed(futures):
                test_dir = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Error generating {test_dir}: {e}")
                    any_failed = True

            if any_failed:
                raise Exception("Generation failed.")

    if do_evaluation:
        any_failed = False
        report = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=evaluate_concurrency) as executor:
            futures = {}
            for category, test in tests:
                test_output_dir = os.path.join(output_dir, "evals", category, test)
                future = executor.submit(evaluate_test, evals_dir, category, test, test_output_dir)
                futures[future] = (category, test_output_dir)
            for future in concurrent.futures.as_completed(futures):
                report_entry, all_ok = future.result()
                report.append(report_entry)
                if not all_ok:
                    any_failed = True

        report.sort(key=lambda x: (x["category"], x["test"]))

        with open(report_path, "w") as f:
            json.dump(report, f)

        if any_failed:
            failed_tests = []
            for r in report:
                category = r['category']
                test = r['test']
                failures = []
                
                for k, v in r.items():
                    if k not in ['category', 'test'] and isinstance(v, dict):
                        if v.get('status') not in ['ok', 'skipped']:
                            if 'error' in v and isinstance(v['error'], list):
                                # For typescript errors, just show count
                                failures.append(f"{k} failed ({len(v['error'])} errors)")
                            elif 'error' in v and isinstance(v['error'], dict) and 'testResults' in v['error']:
                                # For test failures, show failed test names
                                failed_tests_count = v['error'].get('numFailedTests', 0)
                                failures.append(f"{k} failed ({failed_tests_count} tests)")
                            elif 'error' in v:
                                failures.append(f"{k} failed")
                            else:
                                failures.append(f"{k} failed")
                
                if failures:
                    failed_tests.append(f"{category}/{test}: {', '.join(failures)}")
            
            error_msg = "Evaluation failed:\n" + "\n".join(failed_tests)
            raise Exception(error_msg)
