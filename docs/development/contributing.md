# Contributing

## Setup

<pre><code>make install</code></pre>


This installs the package in editable mode with development dependencies and
sets up pre-commit hooks.

## Before Opening A PR

Run:

<pre><code>make check</code></pre>


This runs:

- `ruff check .`
- `mypy src`
- `pytest`

## Coding Guidelines

- Keep pipeline behavior per-file and resumable.
- Return structured results for recoverable file-level failures.
- Preserve deterministic ordering for batch results.
- Add focused tests for new behavior.
- Keep conversion-only paths free of chunking-only dependency imports.

## Branching

The main branch is protected. Use a feature branch for changes.
