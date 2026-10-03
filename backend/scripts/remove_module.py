"""Remove an optional module (e.g. billing, marketing) from this checkout.

Does the steps in docs/adding-a-domain-module.md ("Keeping or dropping the
optional modules"):

1. unlists it in `src/products.py`;
2. deletes `src/<module>/` and its migration (`alembic/versions/*_<module>.py`),
   re-pointing the next migration at the one before it;
3. drops it from the import-linter contracts in `pyproject.toml`;
4. deletes `tests/<module>/`, the tests elsewhere marked with its name, and
   private helpers only they used, and its marker in `pytest.ini`.

Fails if anything it expects is missing, so CI (which runs it on a throwaway
checkout) can't silently stop removing anything. Run from `backend/`:

    uv run python scripts/remove_module.py billing
    uv run poe fix && uv run poe check && uv run poe test

Then reset the database (`python -m src.init_db drop && python -m src.init_db`).
"""

import ast
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent.parent


def fail(message: str) -> NoReturn:
    sys.exit(f"remove_module: {message}")


def unlist(name: str) -> None:
    path = ROOT / "src/products.py"
    text = path.read_text()
    match = re.search(rf"^from src\.{name}\.module import (\w+)\n", text, re.MULTILINE)
    if not match:
        fail(f"no `from src.{name}.module import ...` in {path}")
    constant = match.group(1)
    text = text.replace(match.group(0), "")
    listed = re.search(r"^MODULES: list\[Module\] = \[(.*)\]$", text, re.MULTILINE)
    if not listed or constant not in listed.group(1).split(", "):
        fail(f"{constant} is not listed in MODULES in {path}")
    entries = [e for e in listed.group(1).split(", ") if e != constant]
    text = text.replace(
        listed.group(0),
        f"MODULES: list[Module] = [{', '.join(entries)}]",
    )
    path.write_text(text)


def _revision(text: str, field: str) -> str | None:
    match = re.search(rf'^{field}: str \| None = "?(\w+)"?$', text, re.MULTILINE)
    if not match:
        match = re.search(rf'^{field}: str = "(\w+)"$', text, re.MULTILINE)
    if not match:
        return None
    return None if match.group(1) == "None" else match.group(1)


def drop_migration(name: str) -> None:
    versions = ROOT / "alembic/versions"
    files = sorted(versions.glob(f"*_{name}.py"))
    if len(files) != 1:
        fail(f"expected one migration named *_{name}.py, found {len(files)}")
    removed = files[0].read_text()
    revision = _revision(removed, "revision")
    previous = _revision(removed, "down_revision")
    if revision is None:
        fail(f"no revision id in {files[0].name}")
    for other in versions.glob("*.py"):
        text = other.read_text()
        if other != files[0] and _revision(text, "down_revision") == revision:
            new_down = f'"{previous}"' if previous else "None"
            text = re.sub(
                rf'^down_revision: str \| None = "{revision}"$',
                f"down_revision: str | None = {new_down}",
                text,
                flags=re.MULTILINE,
            )
            text = re.sub(
                rf"^Revises: {revision}$",
                f"Revises: {previous or ''}",
                text,
                flags=re.MULTILINE,
            )
            other.write_text(text)
    files[0].unlink()


def drop_contracts(name: str) -> None:
    path = ROOT / "pyproject.toml"
    text = path.read_text()
    entry = rf'"src\.{name}(?:\.\w+)*"'
    # One entry per line in multi-line lists, then inline entries ("a", "b").
    updated = re.sub(rf"^[ \t]*{entry},\n", "", text, flags=re.MULTILINE)
    updated = re.sub(rf"{entry},[ \t]*|,[ \t]*{entry}", "", updated)
    if updated == text:
        fail(f"no src.{name} entries in the import-linter contracts")
    if f"src.{name}" in updated:
        fail(f"could not remove every src.{name} entry from {path}")
    path.write_text(updated)


def _drop_marked_tests(path: Path, name: str) -> bool:
    source = path.read_text()
    tree = ast.parse(source)
    lines = source.split("\n")
    marked = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(ast.unparse(d) == f"pytest.mark.{name}" for d in node.decorator_list)
    ]
    if not marked:
        return False
    for node in sorted(marked, key=lambda n: -n.lineno):
        start = node.decorator_list[0].lineno - 1
        while start > 0 and lines[start - 1].lstrip().startswith("#"):
            start -= 1
        del lines[start : node.end_lineno]
    # Private, undecorated helpers nothing references any more went with them.
    while True:
        tree = ast.parse("\n".join(lines))
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        orphans = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("_")
            and not node.decorator_list
            and node.name not in used
        ]
        if not orphans:
            break
        for node in sorted(orphans, key=lambda n: -n.lineno):
            del lines[node.lineno - 1 : node.end_lineno]
    path.write_text("\n".join(lines))
    return True


def drop_tests(name: str) -> list[Path]:
    tests = ROOT / "tests"
    shutil.rmtree(tests / name)
    touched = [p for p in tests.rglob("test_*.py") if _drop_marked_tests(p, name)]
    ini = ROOT / "pytest.ini"
    ini.write_text(
        re.sub(rf"^[ \t]+{name}:.*\n", "", ini.read_text(), flags=re.MULTILINE),
    )
    return touched


EXPECTED_ARGC = 2  # script name + module name


def main() -> None:
    if len(sys.argv) != EXPECTED_ARGC:
        fail("usage: remove_module.py <module>")
    name = sys.argv[1]
    package = ROOT / "src" / name
    if not (package / "module.py").is_file():
        fail(f"{package}/module.py not found - not an optional module")
    if not (ROOT / "tests" / name).is_dir():
        fail(f"tests/{name}/ not found")

    unlist(name)
    shutil.rmtree(package)
    drop_migration(name)
    drop_contracts(name)
    touched = drop_tests(name)
    if touched:
        # Imports only the removed tests used.
        subprocess.run(  # noqa: S603 - fixed argv, paths from our own tests dir
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--fix",
                "--select",
                "F401",
                "-q",
                *map(str, touched),
            ],
            cwd=ROOT,
            check=False,
        )
    print(f"remove_module: {name} removed from this checkout")


if __name__ == "__main__":
    main()
