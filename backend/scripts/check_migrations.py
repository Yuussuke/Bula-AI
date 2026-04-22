from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

def extract_assignment(module: ast.Module, name: str) -> ast.AST | None:
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name:
                return node.value

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node.value

    return None


def get_upgrade_function(module: ast.Module) -> ast.AsyncFunctionDef | ast.FunctionDef | None:
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "upgrade":
            return node

    return None


def collect_create_table_calls_in_upgrade(
    module: ast.Module,
) -> list[str]:
    upgrade_function = get_upgrade_function(module)
    if upgrade_function is None:
        return []

    table_names: list[str] = []
    for node in ast.walk(upgrade_function):
        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Attribute):
            continue

        if node.func.attr != "create_table":
            continue

        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "op":
            continue

        if not node.args:
            continue

        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            table_names.append(first_arg.value)

    return table_names


def collect_version_files(versions_directory: Path) -> list[Path]:
    return sorted(path for path in versions_directory.glob("*.py") if path.is_file())


def check_alembic_chain_has_single_head(project_root: Path) -> list[str]:
    errors: list[str] = []

    alembic_config = Config(str(project_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(project_root / "alembic"))
    script_directory = ScriptDirectory.from_config(alembic_config)

    heads = script_directory.get_heads()
    if len(heads) != 1:
        errors.append(
            "Expected exactly one Alembic head, "
            f"but found {len(heads)} heads: {', '.join(heads)}"
        )

    return errors


def check_migration_files(versions_directory: Path) -> list[str]:
    errors: list[str] = []
    create_table_calls: dict[str, list[str]] = defaultdict(list)
    root_revisions = 0

    migration_files = collect_version_files(versions_directory)
    if not migration_files:
        errors.append("No migration files found in alembic/versions.")
        return errors

    for migration_file in migration_files:
        file_content = migration_file.read_text(encoding="utf-8")

        parsed_module = ast.parse(file_content, filename=str(migration_file))

        upgrade_create_table_calls = collect_create_table_calls_in_upgrade(parsed_module)
        for table_name in upgrade_create_table_calls:
            create_table_calls[table_name].append(migration_file.name)

        down_revision_value = extract_assignment(parsed_module, "down_revision")

        if down_revision_value is None:
            errors.append(f"Missing down_revision in {migration_file.name}")
        elif isinstance(down_revision_value, ast.Constant) and down_revision_value.value is None:
            root_revisions += 1

    duplicated_tables = {
        table_name: files
        for table_name, files in create_table_calls.items()
        if len(files) > 1
    }
    for table_name, files in sorted(duplicated_tables.items()):
        errors.append(
            f"Duplicate op.create_table('{table_name}') found in: {', '.join(files)}"
        )

    if root_revisions != 1:
        errors.append(
            "Expected exactly one root migration with down_revision=None, "
            f"but found {root_revisions}."
        )

    return errors


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    versions_directory = project_root / "alembic" / "versions"

    migration_file_errors = check_migration_files(versions_directory)
    alembic_chain_errors = check_alembic_chain_has_single_head(project_root)
    all_errors = migration_file_errors + alembic_chain_errors

    if all_errors:
        print("Migration integrity check failed:")
        for error_message in all_errors:
            print(f"- {error_message}")
        return 1

    print("Migration integrity check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
