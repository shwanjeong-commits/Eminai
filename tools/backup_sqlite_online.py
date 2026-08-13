import argparse
import sqlite3
from pathlib import Path


def backup_database(source_path: Path, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source_path) as source, sqlite3.connect(output_path) as target:
        source.backup(target)
        integrity = target.execute("pragma integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"backup integrity check failed: {integrity}")
    return integrity


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an online SQLite backup and verify it.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    integrity = backup_database(args.source, args.output)
    print(f"backup={args.output}")
    print(f"integrity={integrity}")


if __name__ == "__main__":
    main()
