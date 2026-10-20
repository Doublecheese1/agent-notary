"""Create a source release without local dependencies, caches or secrets."""
from pathlib import Path
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
target = Path(sys.argv[1]).resolve()
excluded_parts = {
    "node_modules", ".testdeps", ".local-testdeps", ".qa-deps", ".qa-tmp", ".pnpm-store",
    "__pycache__", ".git",
}

with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in excluded_parts for part in path.parts):
            continue
        if path.suffix in {".pyc", ".zip"} or path.name == ".env":
            continue
        archive.write(path, Path("agent-notary-launch") / path.relative_to(root))

print(target)
