# General Principles

Write code that is easy for another engineer to understand six months from now.

Prioritize:
1. Correctness
2. Readability
3. Simplicity
4. Performance (only when justified)

Avoid clever code.

---

# Python Version

Target Python 3.12+ unless the project specifies otherwise.

Prefer standard library features before introducing new dependencies.

---

# Code Style

Follow PEP 8.

Use:
- pathlib instead of os.path
- f-strings
- dataclasses where appropriate
- enum.Enum instead of magic constants
- context managers for resources

Avoid:
- wildcard imports
- mutable default arguments
- unnecessary globals
- deeply nested conditionals

Prefer explicit code over implicit behavior.

---

# Type Hints

Use type hints on all public APIs.

Use modern built-in generic syntax:

list[str]
dict[str, int]

instead of typing.List.

---

# Functions

Functions should generally do one thing.

Prefer small functions over long functions.

If a function exceeds roughly 40-50 lines, consider whether it should be split.

Avoid boolean flag parameters when separate functions would be clearer.

---

# Classes

Classes should have a single responsibility.

Favor composition over inheritance.

Avoid unnecessary abstraction.

---

# Errors

Raise meaningful exceptions.

Do not silently ignore errors.

Validate inputs at system boundaries.

Include useful context in exception messages.

---

# Logging

Use the logging module.

Do not use print() except for CLI output.

Log enough information to diagnose failures without exposing secrets.

---

# Testing

Whenever modifying behavior:

- update existing tests
- or create new tests

Prefer pytest.

Tests should verify behavior rather than implementation.

---

# Documentation

Public modules, classes, and functions should have docstrings.

Complex logic should include comments explaining *why*, not *what*.

Avoid obvious comments.

---

# Dependencies

Avoid introducing new packages unless they provide substantial value.

Discuss major dependency additions before using them.

A human must approve any new dependencies added to the project.

---

# Refactoring

Leave the code cleaner than you found it.

Reduce duplication.

Improve naming.

Remove dead code when encountered.

---

# Performance

Do not optimize prematurely.

When optimizing:
- identify the bottleneck
- explain the reason
- preserve readability where practical

---

# Before Finishing

Before considering work complete:

- Ensure code is formatted.
- Ensure linting passes.
- Ensure tests pass.
- Remove debug code.
- Remove commented-out code.
- Check for unused imports.
- Check for obvious edge cases.

---

# Communication

When proposing changes:

- Explain the reasoning.
- Mention tradeoffs.
- Call out assumptions.
- Ask before making large architectural changes.

Do not invent requirements.

If uncertain, say so.
