import ast
from pathlib import Path

DOCUMENTS_SOURCE = Path(__file__).parents[2] / "src" / "magi" / "documents"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_documents_domain_and_application_do_not_import_infrastructure_frameworks() -> None:
    inward_files = (
        *DOCUMENTS_SOURCE.joinpath("domain").rglob("*.py"),
        *DOCUMENTS_SOURCE.joinpath("application").rglob("*.py"),
    )
    forbidden_prefixes = (
        "fastapi",
        "minio",
        "sqlalchemy",
        "magi.documents.infrastructure",
        "magi.ingestion.infrastructure",
        "magi.retrieval.infrastructure",
    )

    violations = {
        str(path.relative_to(DOCUMENTS_SOURCE)): sorted(
            module for module in imported_modules(path) if module.startswith(forbidden_prefixes)
        )
        for path in inward_files
    }

    assert not {path: modules for path, modules in violations.items() if modules}
