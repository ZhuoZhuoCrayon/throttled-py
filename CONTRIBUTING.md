# Contributing to throttled-py

Thank you for your interest in contributing to throttled-py!
This guide will help you get started and ensure a smooth review process. If anything is unclear, please feel free to open an issue or ask in your pull request.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [PR Checklist](#pr-checklist)

## Getting Started

1. Fork the repository and clone your fork.
2. Create a branch from `main` for your changes.
3. Follow the [Development Setup](#development-setup) to configure your environment.
4. Make your changes, following the guidelines below.
5. Submit a pull request.

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

### Install Dependencies

```bash
uv sync --group all
```

### Set Up Pre-commit Hooks (prek)

This project uses [prek](https://prek.j178.dev/) to run lint and format checks automatically before each commit.

```bash
# Install git hooks (first time only)
uv run prek install
```

Verify the installation:

```bash
# Should list: check-merge-conflict, ruff, ruff-format
uv run prek list
```

You can also run the hooks manually:

```bash
# Run on specific files
uv run prek run --files <changed-files>

# Run on all files
uv run prek run --all-files
```

> **Important**: Please run prek locally before pushing. CI will block merging if the Code Quality check fails.

## Code Style

### Linting (ruff)

All code is linted and formatted by [ruff](https://docs.astral.sh/ruff/). The full configuration is in [`pyproject.toml`](pyproject.toml). Key settings:

- **Line length**: `89` characters
- **Docstring style**: reStructuredText (`:param:`, `:return:`). See [Docstrings](#docstrings) below.
- **Enabled rule sets**:

  | Code | Rule Set | Code | Rule Set |
  |------|----------|------|----------|
  | `F` | Pyflakes | `SIM` | flake8-simplify |
  | `E` / `W` | pycodestyle | `G` / `LOG` | flake8-logging |
  | `C90` | mccabe (complexity) | `TRY` | tryceratops |
  | `I` | isort | `B` | flake8-bugbear |
  | `D` | pydocstyle | `T10` / `T20` | flake8-debugger / print |
  | `UP` | pyupgrade | `C4` | flake8-comprehensions |
  | `N` | pep8-naming | `RET` | flake8-return |
  | `PL` | Pylint | `PERF` | Perflint |
  | `PT` | flake8-pytest-style | `PIE` / `PYI` | flake8-pie / pyi |

### Type Hints

Please add type annotations to all variables. Use Python 3.10+ built-in generics:

```python
# Good
result: list[str] = []
data: dict[str, int] = {}

# Bad - deprecated typing generics
from typing import List, Dict
result: List[str] = []
```

### Docstrings

Please use [**reStructuredText (rst)** style](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html) consistently. This is required because the project uses [Sphinx](https://www.sphinx-doc.org/) with `autodoc` to generate API documentation from docstrings.
Sphinx parses rst syntax (`:param:`, `:return:`), so Google-style (`Args:`, `Returns:`) will not render correctly in the generated docs.

```python
# Good - rst style (parsed correctly by Sphinx autodoc)
def build_hook_chain(
    hooks: list[Hook],
    do_limit: Callable[[], "RateLimitResult"],
    context: HookContext,
) -> Callable[[], "RateLimitResult"]:
    """Build a hook chain using middleware pattern.

    :param hooks: List of hooks to chain.
    :param do_limit: The actual rate limit function to be wrapped.
    :param context: The hook context containing rate limit metadata.
    :return: A callable that executes the hook chain.
    """

# Bad - Google style (will NOT render in Sphinx API docs)
def build_hook_chain(...):
    """Build a hook chain.

    Args:
        hooks: List of hooks to chain.

    Returns:
        A callable.
    """
```

## Testing Guidelines

### Class-Based Tests with `@classmethod`

Please write all tests as **class-based** with the `@classmethod` decorator. Standalone test functions are not accepted.

```python
# Good
class TestBuildHookChain:
    @classmethod
    def test_on_limit__multi_hooks(
        cls, hook_context: HookContext, rate_limit_result: RateLimitResult
    ) -> None:
        """Multiple hooks should execute in correct order."""
        ...

# Bad
def test_build_hook_chain_multi_hooks():
    ...
```

### Test Naming

Please use the format `test_{function_name}__{case_description}` with double underscores separating the target and the case:

```python
class TestOTelHook:
    def test_allowed_request__records_metrics(cls, ...): ...
    def test_denied_request__records_metrics(cls, ...): ...
    def test_custom_cost__recorded(cls, ...): ...
```

### Mocking External Dependencies

Please use mocks for external dependencies (e.g., OpenTelemetry SDK). Understanding the request-response interface and mocking it accordingly keeps tests simple:

```python
@pytest.fixture
def mock_meter() -> MagicMock:
    meter: MagicMock = MagicMock(name="Meter")
    meter.create_counter.return_value = MagicMock(name="Counter")
    meter.create_histogram.return_value = MagicMock(name="Histogram")
    return meter
```

### Other Test Rules

- **No duplicate fixtures**: Please share common fixtures via `conftest.py`.
- **No empty files**: Please remove empty `conftest.py` files.
- **Benchmarks**: Please add `@pytest.mark.skip(reason="skip benchmarks")` to benchmark test classes.

### Coverage Requirements

CI checks test coverage via [Codecov](https://about.codecov.io/). Please make sure your changes meet the following thresholds:

| Scope | Target |
|-------|--------|
| **Project** (overall) | 85% |
| **Patch** (changed lines) | 65% |

You can check coverage locally:

```bash
uv run pytest --cov=throttled --cov-report=term-missing tests/
```

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -x

# Run a specific test file
uv run pytest tests/test_hooks.py -v
```

## Documentation

This project uses [Sphinx](https://www.sphinx-doc.org/) with `autodoc` to generate API documentation from docstrings. If you're adding or modifying public APIs, please make sure the docs build correctly:

```bash
# Build HTML docs (sphinx is included in `uv sync --group all`)
cd docs
uv run make html

# Preview locally at http://localhost:8000
python -m http.server 8000 --directory build/html
```

The generated docs will be in `docs/build/html/`. Please use rst-style docstrings (`:param:`, `:return:`) so Sphinx can parse them correctly — see [Docstrings](#docstrings) for details.

## Commit Conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/). Commit messages are validated by [commitlint](https://commitlint.js.org/) in CI (GitHub Actions).

### Format

```
<type>: <description> (#<issue-number>)
```

### Allowed Types

| Type | Description |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `ci` | Changes to CI configuration |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Build process or tooling changes |

### Examples

```bash
# Good
git commit -m "feat: add hook system with OpenTelemetry support (#37)"
git commit -m "fix: add @wraps decorator for metadata preservation (#120)"
git commit -m "docs: update contributing guidelines (#127)"

# Bad - will fail CI
git commit -m "updated hooks"           # missing type
git commit -m "Feat: add hooks"         # uppercase type
git commit -m "feat : add hooks"        # space before colon
```

## Pull Request Process

### 1. Keep Your Branch Up to Date

Rebase onto the latest `main` before submitting:

```bash
git fetch upstream
git rebase upstream/main
```

### 2. Squash and Push

Before pushing, please squash your commits into a single commit with a valid [Conventional Commits](#commit-conventions) message. CI validates the commit message via commitlint — squashing helps it pass on the first push.

```bash
# Squash N commits into one
git rebase -i HEAD~N

# Verify the message format before pushing
git log --oneline -1
# Should show: <type>: <description> (#<issue-number>)
```

### 3. Respond to Reviews

- Please address all review comments before requesting re-review.
- Rebase and squash again when the maintainer asks you to sync with `main`.
- Please re-run prek after making changes to ensure lint checks still pass.

### 4. CI Checks

All of the following must pass before merging:

| Check | What It Does |
|-------|-------------|
| **Code Quality** | ruff lint + format via prek |
| **Tests** | pytest across Python 3.10 - 3.14 + PyPy |
| **Commitlint** | Validates commit message format |
| **Coverage** | Reports test coverage (patch + project) |

## PR Checklist

Before submitting your pull request, please verify the following:

- [ ] `uv run prek run --all-files` passes locally
- [ ] `uv run pytest tests/ -x` passes locally
- [ ] Type annotations added to all variables
- [ ] Docstrings use reStructuredText style (`:param:`, `:return:`)
- [ ] Tests are class-based with `@classmethod`
- [ ] Test names follow `test_{func}__{case}` format
- [ ] No empty files or unused code
- [ ] No duplicate fixtures
- [ ] Commit message follows Conventional Commits (`<type>: <description> (#issue)`)
- [ ] Commits are squashed and rebased onto `main`
