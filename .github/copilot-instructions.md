# GitHub Copilot Code Review Instructions

This document provides comprehensive code review guidelines for the throttled-py project,
ensuring consistency and quality in all pull requests reviewed by GitHub Copilot.

> **⚠️ CRITICAL INSTRUCTION**: Read `CONTRIBUTING.md` before every review.
> Treat it as the source of truth for project conventions and workflow.
>
> **⚠️ CRITICAL INSTRUCTION**: Every PR review summary **MUST** begin with:
> `✓ Review conducted following guidelines defined in .github/copilot-instructions.md`

[TOC]

## Core Review Principles

As a Copilot agent reviewing this project, prioritize the following principles:

1.  **Clarity and Maintainability**: Code must be easy to read, understand, and change.
2.  **Correctness and Reliability**: Ensure algorithms are implemented correctly. Pay close attention to concurrency (`asyncio`, `threading`), thread safety, and atomic operations, as they are critical for a rate-limiting library.
3.  **Performance**: Rate limiting must be fast. Review data structures and algorithms in hot paths.
4.  **Test Relevance**: New behavior should be covered by tests proportional to its risk.

---

## Documentation Review Guidelines

### English Documentation

English documentation must follow the [Google Markdown Style Guide](https://google.github.io/styleguide/docguide/style.html).

**Key Requirements:**

- **Line Length**: Maintain an 80-character line limit (exceptions: links, tables, headings, code blocks)
- **Headings**:
  - Use ATX-style headings (`#`, `##`, etc.)
  - Use unique and descriptive names for each heading
  - Add spacing after `#` and newlines before/after headings
  - Use only one H1 heading per document
- **Lists**: Use lazy numbering for long ordered lists
- **Code Blocks**:
  - Always declare the language for syntax highlighting
  - Prefer fenced code blocks (```) over indented code blocks
- **Links**:
  - Use informative link titles
  - Use reference links for long URLs or repeated links
  - Define reference links after their first use
- **Tables**: Use tables only for tabular data; prefer lists when appropriate
- **Trailing Whitespace**: Do not use trailing whitespace
- **Document Layout**: Follow this structure:
  ```markdown
  # Document Title

  Short introduction.

  [TOC]

  ## Topic

  Content.

  ## See also

  * Links to related resources
  ```

### Chinese Documentation

Chinese documentation must follow the [Chinese Copywriting Guidelines](https://github.com/ruanyf/document-style-guide).

**Key Requirements:**

- **Spacing**:
  - Add space between Chinese and English characters
  - Add space between Chinese and numbers
  - Add space between numbers and units (except for degrees, percentages)
- **Punctuation**:
  - Use full-width punctuation for Chinese text
  - Use half-width punctuation for English text and code
  - Do not add space before or after full-width punctuation
- **Nouns**:
  - Use correct capitalization for proper nouns (e.g., GitHub, Python, macOS)
  - Maintain brand name capitalization
- **Numbers**:
  - Use Arabic numerals for statistics and measurements
  - Numbers with more than 4 digits should use comma separators (e.g., 1,000)
- **Links**: Ensure link text is meaningful and descriptive

---

## Python Code Review Guidelines

As an expert-level Python engineer, provide professional feedback on the following aspects:

### 1. Code Quality & Style

- **PEP 8 Compliance**: Ensure code follows [PEP 8](https://peps.python.org/pep-0008/) style guide
- **Type Hints**: Use type hints (PEP 484) for function signatures and complex variables
- **Docstrings**: Review docstrings against `CONTRIBUTING.md`; public API docstrings should render correctly in Sphinx
- **Line Length and Formatting**: Use `pyproject.toml` as the source of truth
- **Import Organization**:
  - Group imports: standard library, third-party, local (as enforced by `ruff`).
  - Use absolute imports over relative imports
  - Avoid wildcard imports (`from module import *`)

### 2. Naming Conventions

- **Variables**: `snake_case` for variables and functions
- **Classes**: `PascalCase` for class names
- **Constants**: `UPPER_SNAKE_CASE` for constants
- **Private Members**: Prefix with single underscore `_private_method`
- **Name Clarity**: Use descriptive, meaningful names that reveal intent
- **Avoid Abbreviations**: Except for well-known abbreviations (e.g., `id`, `url`, `http`)

### 3. Design Patterns & Architecture

- **SOLID Principles**:
  - Single Responsibility: Each class/function should have one reason to change
  - Open/Closed: Open for extension, closed for modification
  - Liskov Substitution: Subtypes must be substitutable for base types
  - Interface Segregation: Many specific interfaces are better than one general interface
  - Dependency Inversion: Depend on abstractions, not concretions
- **Design Patterns**: Apply appropriate patterns (Factory, Strategy, Observer, etc.)
- **Separation of Concerns**: Separate business logic, data access, and presentation layers

### 4. Performance Optimization

- **Algorithm Efficiency**:
  - Evaluate time and space complexity
  - Suggest more efficient algorithms when applicable
- **Data Structures**: Choose appropriate data structures (dict vs. list, set for lookups, etc.)
- **Lazy Evaluation**: Use generators and iterators for large datasets
- **Caching**: Apply memoization or caching for expensive operations
- **Profiling**: Recommend profiling for performance-critical code
- **Avoid Premature Optimization**: Optimize only when necessary

### 5. Asynchronous Programming

- **Async/Await**: Use `async`/`await` properly for I/O-bound operations
- **Concurrency**:
  - Use `asyncio` for async operations
  - Use `threading` for I/O-bound tasks
  - Use `multiprocessing` for CPU-bound tasks
- **Event Loop Management**: Properly manage event loops and avoid blocking operations
- **Resource Cleanup**: Ensure proper cleanup with `async with` context managers

### 6. Error Handling & Reliability

- **Exception Handling**:
  - Catch specific exceptions, not generic `Exception`
  - Use `try-except-else-finally` appropriately
  - Don't use exceptions for flow control
- **Custom Exceptions**: Create custom exception classes for domain-specific errors
- **Logging**: Use `logging` module instead of `print()` statements
- **Validation**: Validate inputs and handle edge cases
- **Defensive Programming**: Check preconditions and postconditions

### 7. Documentation & Maintainability

- **Code Comments**:
  - Explain "why", not "what"
  - Keep comments up-to-date with code changes
  - Avoid obvious comments

### 8. Specific to Rate Limiting Projects

- **Thread Safety**: Ensure rate limiters are thread-safe when needed
- **Atomic Operations**: Use atomic operations for counter updates
- **Distributed Systems**: Consider distributed rate limiting with Redis or similar
- **Algorithm Selection**: Choose appropriate rate limiting algorithms:
  - Token Bucket: For bursty traffic with average rate control
  - Leaky Bucket: For smooth, constant output rate
  - Fixed Window: Simple but can have boundary issues
  - Sliding Window: More accurate but resource-intensive
  - GCRA (Generic Cell Rate Algorithm): Precise and memory-efficient
- **Performance**: Rate limiters should add minimal latency
- **Accuracy**: Balance between accuracy and performance
- **Resource Cleanup**: Properly clean up expired entries in stores

---

## Industry Best Practices

### Code Review Checklist

- [ ] Code follows project style guide and conventions
- [ ] All tests pass and new tests are added for new features
- [ ] Documentation is updated for API changes
- [ ] No security vulnerabilities introduced
- [ ] Performance considerations are addressed
- [ ] Error handling is comprehensive
- [ ] Code is readable and maintainable
- [ ] No code duplication (DRY principle)
- [ ] Dependencies are justified and minimal
- [ ] Backwards compatibility is maintained (or breaking changes are documented)

### Continuous Improvement

- **Refactoring**: Suggest refactoring opportunities for code health
- **Technical Debt**: Identify and document technical debt
- **Deprecations**: Follow proper deprecation process (warnings, docs, removal timeline)
- **Benchmarks**: Include benchmarks for performance-critical changes
- **Observability**: Add logging, metrics, and tracing where appropriate

---

## Review Tone & Communication

- **Be Constructive**: Focus on improving the code, not criticizing the author
- **Be Specific**: Provide concrete examples and suggestions
- **Be Educational**: Explain the reasoning behind suggestions
- **Acknowledge Good Work**: Recognize well-written code and good practices
- **Ask Questions**: Use questions to understand intent rather than making assumptions
- **Prioritize**: Distinguish between critical issues and nitpicks

---

## References

- [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 257 – Docstring Conventions](https://peps.python.org/pep-0257/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [The Zen of Python (PEP 20)](https://peps.python.org/pep-0020/)
- [Google Markdown Style Guide](https://google.github.io/styleguide/docguide/style.html)
- [Chinese Copywriting Guidelines](https://github.com/ruanyf/document-style-guide)
- [Effective Python: 90 Specific Ways to Write Better Python](https://effectivepython.com/)
- [Clean Code: A Handbook of Agile Software Craftsmanship](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)

---

**Last Updated**: 2025-11-16
