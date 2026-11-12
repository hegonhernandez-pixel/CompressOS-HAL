"""Non-mutating ELF indexer. It snapshots files; it never patches executables."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List
from .registry import CasRegistry


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent)
        return True
    except ValueError:
        return False


def index_tree(root: str | Path, registry: CasRegistry, max_files: int = 1000) -> List[Dict[str, object]]:
    base = Path(root)
    if not base.is_dir():
        raise ValueError("index root must be a directory")
    if max_files < 1 or max_files > 100000:
        raise ValueError("max_files must be between 1 and 100000")
    cas_root = registry.root.resolve()
    indexed = []
    for current, directories, filenames in os.walk(base, followlinks=False):
        current_path = Path(current)
        if _inside(current_path, cas_root):
            directories[:] = []
            continue
        directories[:] = sorted(
            d for d in directories
            if not (current_path / d).is_symlink()
            and not _inside(current_path / d, cas_root)
        )
        for filename in sorted(filenames):
            candidate = current_path / filename
            if candidate.is_symlink() or not candidate.is_file() or _inside(candidate, cas_root):
                continue
            try:
                with candidate.open("rb") as stream:
                    if stream.read(4) != b"\x7fELF":
                        continue
                record = registry.ingest(candidate)
                record["source_path"] = str(candidate)
                record["translation"] = "indexed_only"
                record["binary_modified"] = False
                indexed.append(record)
                if len(indexed) >= max_files:
                    return indexed
            except (OSError, ValueError):
                continue
    return indexed
