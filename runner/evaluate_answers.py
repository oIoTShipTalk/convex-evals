import os
import re
import json
import argparse
import shutil
import sys
from convex_backend import deploy, convex_backend, run_tests
from typescript import setup_js, lint_js, typecheck_js
import concurrent.futures
from errors import error_status, VerificationError
import threading
import tempfile

# Use a lock for cleaner console output
print_lock = threading.Lock()

def print_status(msg: str):
    with print_lock:
        print(msg)

def format_test_error(e: Exception) -> dict:
    error_dict = error_status(e)
    if isinstance(e, VerificationError) and len(e.args) > 1 and isinstance(e.args[1], dict):
        test_results = e.args[1].get("testResults", [])
        failures = []
        for test_result in test_results:
            for assertion in test_result.get("assertionResults", []):
                if assertion.get("status") == "failed":
                    title = assertion.get("title", "Unknown test")
                    messages = assertion.get("failureMessages", [])
                    if messages:
                        # Extract the actual error message from the stack trace
                        message = messages[0].split("\n")[0]
                        if "Server Error" in messages[0]:
                            # For server errors, get the line after "Server Error"
                            lines = messages[0].split("\n")
                            for i, line in enumerate(lines):
                                if "Server Error" in line and i + 1 < len(lines):
                                    message = lines[i + 1].strip()
                                    break
                        failures.append(f"{title}: {message}")
                    else:
                        failures.append(f"{title}: No error message")
        if failures:
            error_dict["failures"] = failures
    return error_dict

def evaluate_answer(evals_dir: str, category: str, test: str, direct_output: bool = False):
    test_dir = os.path.join(evals_dir, category, test)
    answer_dir = os.path.join(test_dir, "answer")

    if not os.path.exists(answer_dir):
        print_status(f"No answer directory found for {category}/{test}")
        return None, False

    report_entry = {
        "category": category,
        "test": test,
        "setup": {"status": "skipped"},
        "typecheck": {"status": "skipped"},
        "lint": {"status": "skipped"},
        "deploy": {"status": "skipped"},
        "tests": {"status": "skipped"},
    }

    # Create a temporary project directory with the answer contents
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temp dir: {temp_dir}")
        project_dir = os.path.join(temp_dir, "project")
        os.makedirs(project_dir, exist_ok=True)
        shutil.copytree(answer_dir, project_dir, dirs_exist_ok=True)

        # Ensure package.json exists
        if not os.path.exists(os.path.join(project_dir, "package.json")):
            with open(os.path.join(project_dir, "package.json"), "w") as f:
                json.dump({
                    "name": f"convex-eval-{category}-{test}",
                    "private": True,
                    "dependencies": {
                        "convex": "^1.0.0"
                    }
                }, f)

        try:
            setup_js(temp_dir, direct_output)
            report_entry["setup"] = {"status": "ok"}
        except Exception as e:
            print_status(f"Error setting up {category}/{test}: {e}")
            report_entry["setup"] = {"status": "failed", "error": str(e)}
            return report_entry, False

        try:
            typecheck_js(temp_dir, direct_output)
            report_entry["typecheck"] = {"status": "ok"}
        except Exception as e:
            print_status(f"Error typechecking {category}/{test}: {e}")
            report_entry["typecheck"] = error_status(e)

        try:
            lint_js(temp_dir, direct_output)
            report_entry["lint"] = {"status": "ok"}
        except Exception as e:
            print_status(f"Error linting {category}/{test}: {e}")
            report_entry["lint"] = error_status(e)

        backend_dir = os.path.join(temp_dir, "backend")
        os.makedirs(backend_dir, exist_ok=True)

        with convex_backend(backend_dir) as backend:
            try:
                deploy(backend, project_dir)
                report_entry["deploy"] = {"status": "ok"}
            except Exception as e:
                print_status(f"Error deploying {category}/{test}: {e}")
                report_entry["deploy"] = error_status(e)
                return report_entry, False

            test_file = os.path.abspath(os.path.join(test_dir, "grader.test.ts"))
            if os.path.exists(test_file):
                try:
                    # Pass the same backend for both since we're testing the answer against itself
                    run_tests(backend, backend, test_file, direct_output)
                    report_entry["tests"] = {"status": "ok"}
                except Exception as e:
                    if not direct_output:
                        print_status(f"Error running tests for {category}/{test}:")
                        error_info = format_test_error(e)
                        if "failures" in error_info:
                            for failure in error_info["failures"]:
                                print_status(f"  ❌ {failure}")
                        report_entry["tests"] = error_info
                    else:
                        raise

    all_ok = all(v["status"] == "ok" for k, v in report_entry.items() if "status" in v)
    status = "✅" if all_ok else "❌"
    if not direct_output:
        print_status(f"{status} {category}/{test}")
    return report_entry, all_ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run evaluation suite against answer directories"
    )
    parser.add_argument("--evals-dir", help="Evals directory", default="evals")
    parser.add_argument("--test-filter", "-k", help="Filter tests by regexp")
    parser.add_argument("--output", "-o", help="Output report file", default="answer_report.json")
    parser.add_argument("--direct-output", action="store_true", help="Print tool output directly to stdout")
    parser.add_argument("output_dir", nargs="?", help="Output directory for test results")
    parser.add_argument("category", nargs="?", help="Category to test")
    parser.add_argument("test", nargs="?", help="Test to run")

    args = parser.parse_args()

    # If output_dir, category, and test are provided, run in direct output mode
    if args.output_dir and args.category and args.test:
        evaluate_answer("evals", args.category, args.test, direct_output=True)
        sys.exit(0)

    # Otherwise, run in report mode
    test_filter = re.compile(args.test_filter) if args.test_filter else None
    tests = [
        (category, test)
        for category in os.listdir(args.evals_dir)
        if os.path.isdir(os.path.join(args.evals_dir, category))
        for test in os.listdir(os.path.join(args.evals_dir, category))
        if os.path.isdir(os.path.join(args.evals_dir, category, test))
        if test_filter is None or test_filter.match(f"{category}/{test}")
    ]
    tests.sort()

    print_status(f"Running {len(tests)} tests")
    report = []
    any_failed = False

    for category, test in tests:
        result = evaluate_answer(args.evals_dir, category, test, direct_output=args.direct_output)
        if result is not None:
            report_entry, all_ok = result
            report.append(report_entry)
            if not all_ok:
                any_failed = True

    report.sort(key=lambda x: (x["category"], x["test"]))

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    print_status(f"\nReport written to {args.output}")
    if any_failed:
        print_status("\nSome tests failed. See report for details.")
        exit(1)
    else:
        print_status("\nAll tests passed!")