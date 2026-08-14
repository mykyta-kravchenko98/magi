import ast
from pathlib import Path

RETRIEVAL_SOURCE = Path(__file__).parents[2] / "src" / "magi" / "retrieval"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_domain_and_application_do_not_import_retrieval_infrastructure() -> None:
    inward_files = (
        *RETRIEVAL_SOURCE.joinpath("domain").rglob("*.py"),
        *RETRIEVAL_SOURCE.joinpath("application").rglob("*.py"),
    )

    violations = {
        str(path.relative_to(RETRIEVAL_SOURCE)): sorted(
            module
            for module in imported_modules(path)
            if module.startswith("magi.retrieval.infrastructure")
        )
        for path in inward_files
    }

    assert not {path: modules for path, modules in violations.items() if modules}
