import ast
from pathlib import Path

INGESTION_SOURCE = Path(__file__).parents[2] / "src" / "magi" / "ingestion"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_domain_and_application_do_not_import_ingestion_infrastructure() -> None:
    inward_files = (
        *INGESTION_SOURCE.joinpath("domain").rglob("*.py"),
        *INGESTION_SOURCE.joinpath("application").rglob("*.py"),
    )

    violations = {
        str(path.relative_to(INGESTION_SOURCE)): sorted(
            module
            for module in imported_modules(path)
            if module.startswith("magi.ingestion.infrastructure")
        )
        for path in inward_files
    }

    assert not {path: modules for path, modules in violations.items() if modules}
