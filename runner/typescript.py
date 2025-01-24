import subprocess
import os
import json
from errors import VerificationError


def setup_js(output_dir: str, direct_output: bool = False):
    project_dir = os.path.abspath(os.path.join(output_dir, "project"))
    if direct_output:
        subprocess.check_call(
            ["bun", "install"],
            cwd=project_dir,
        )
        subprocess.check_call(
            ["bunx", "convex", "codegen", "--typecheck", "disable", "--init"],
            cwd=project_dir,
        )
    else:
        subprocess.run(
            ["bun", "install"],
            cwd=project_dir,
            check=True,
        )
        print("Install OK!")
        subprocess.run(
            ["bunx", "convex", "codegen", "--typecheck", "disable", "--init"],
            cwd=project_dir,
            check=True,
        )
        print("Codegen OK!")


def typecheck_js(output_dir: str, direct_output: bool = False):
    convex_dir = os.path.abspath(os.path.join(output_dir, "project", "convex"))
    if direct_output:
        subprocess.check_call(
            ["bunx", "tsc", "-noEmit", "-p", convex_dir],
        )
    else:
        done = subprocess.run(
            ["bunx", "tsc", "-noEmit", "-p", convex_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        if done.returncode != 0:
            raise VerificationError("Typechecking failed", done.stdout.splitlines())
        print("Typecheck OK!")


def lint_js(output_dir: str, direct_output: bool = False):
    convex_dir = os.path.abspath(os.path.join(output_dir, "project", "convex"))
    if direct_output:
        subprocess.check_call(
            ["bunx", "eslint", "-c", "eslint.config.mjs", convex_dir],
        )
    else:
        done = subprocess.run(
            ["bunx", "eslint", "-c", "eslint.config.mjs", convex_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        if done.returncode != 0:
            errors = json.loads(done.stdout)
            for error in errors:
                error.pop("source", None)
            raise VerificationError("Linting failed", errors)
        print("ESLint OK!")
