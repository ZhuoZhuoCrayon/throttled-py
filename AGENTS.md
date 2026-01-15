# AI Agent Instructions

Instructions for AI assistants working with throttled-py.

## Project Overview

- **Package Manager**: [uv](https://docs.astral.sh/uv/)
- **Build System**: Hatch
- **Python**: >= 3.10

## Task Instructions

**MUST**: When executing any task, begin with:
> ✓ Conducted following guidelines defined in `<instruction_file_path>`

### PR Review

Follow `.github/copilot-instructions.md`.

### Release Preparation

When message contains `release` with version changelog or release draft URL:

Follow `.github/instructions/release.instructions.md`.
