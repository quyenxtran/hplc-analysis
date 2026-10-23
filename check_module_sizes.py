"""Hard 5,000-byte limit for code, tests, and text documentation (not SVG assets)."""
from pathlib import Path


LIMIT = 5000
TEXT_SUFFIXES = {".py", ".md", ".txt", ".yml", ".yaml", ".toml", ".js", ".mjs", ".cjs", ".html", ".css"}
IGNORED_DIRS = {".git", "__pycache__", ".venv", "venv", ".cache", ".pytest_cache",
                "batch_results", "editing_results", "peak_area", "output"}


def source_files(root):
    root = Path(root)
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES
                  and not any(part in IGNORED_DIRS for part in p.relative_to(root).parts[:-1]))


def oversized_files(root, limit=LIMIT):
    root = Path(root)
    return [(str(p.relative_to(root)), p.stat().st_size) for p in source_files(root)
            if p.stat().st_size > limit]


def main():
    root = Path(__file__).resolve().parent
    violations = oversized_files(root)
    for path, size in violations:
        print(f"FAIL: {path}: {size} bytes > {LIMIT}")
    if violations:
        raise SystemExit(1)
    files = source_files(root)
    largest = max((p.stat().st_size, str(p.relative_to(root))) for p in files)
    print(f"All {len(files)} source/documentation files <= {LIMIT} bytes. Largest: {largest[1]} ({largest[0]} bytes).")


if __name__ == "__main__":
    main()
