---
name: test-focus
description: Run only the tests relevant to files changed in the current git diff. Scopes backend pytest runs to changed modules and skips unrelated test files to give fast, targeted feedback.
---

# Test Focus

Run only the tests that are relevant to the current changes, rather than the full suite.

## Arguments

The user invoked this with: $ARGUMENTS

No arguments required. Operates on the current working tree diff.

## Workflow

### Step 1 - Identify changed files

```bash
git diff --name-only HEAD
```

Also check staged changes:
```bash
git diff --name-only --cached
```

Combine both lists. If the diff is empty, fall back to the last commit:
```bash
git diff --name-only HEAD~1 HEAD
```

### Step 2 - Map changed files to test files

#### Backend (`backend/src/`)

For each changed backend file, derive the corresponding test file path:

| Changed file | Test file pattern |
|---|---|
| `backend/src/routers/foo.py` | `backend/tests/api/test_foo.py` |
| `backend/src/services/foo_service.py` | `backend/tests/api/test_foo.py` |
| `backend/src/repositories/foo_repository.py` | `backend/tests/api/test_foo.py` |
| `backend/src/models/foo.py` | `backend/tests/api/test_foo.py` |
| `backend/src/schemas/foo.py` | `backend/tests/api/test_foo.py` |
| `backend/src/billing/*.py` | `backend/tests/api/test_billing_*.py` |
| `backend/src/core/*.py` | run full suite |

Tests are split into `backend/tests/api/` (integration, uses test client) and `backend/tests/unit/` (unit tests). Check both directories when looking for coverage.

Verify each derived test file exists before adding it to the run list:
```bash
ls backend/tests/api/
```

#### Frontend (`frontend/src/`)

The frontend currently has no test suite. If vitest or similar is added in future, check `frontend/package.json` for a `test` script and run it scoped to changed files.

### Step 3 - Run backend tests

If specific test files were identified:
```bash
cd backend && uv run pytest <test-file-1> <test-file-2> -v
```

If a core file changed or no specific mapping was found, run the full suite:
```bash
cd backend && uv run pytest ./tests -v
```

### Step 4 - Report results

Summarize:
- Which test files were run and why
- Pass/fail counts
- Any failures with the relevant error message
- Whether any changed files had no corresponding test (flag as a coverage gap)

## Notes

- Backend tests use SQLite in-memory; no running database needed
- `asyncio_mode = auto` - all test functions can be `async`
- `tests/conftest.py` provides pre-seeded fixtures; do not seed manually before running tests
