default:
    @just --list

format:
    just format-python
    just format-js

lint:
    just lint-python

format-python:
    pdm run black .

lint-python:
    pdm run ruff check .

format-js:
    bunx prettier --write .