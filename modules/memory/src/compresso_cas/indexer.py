"""Non-mutating ELF indexer. It snapshots files; it never patches executables."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List
from .registry import CasRegistry


def index_tree(root: str | Path, registry: CasRegistry, max_files: int = 1000) -> List[Dict[str, object]]:
    base = Path(root)
    if not base.is_dir():
        raise ValueError("index root must be a directory")
    if max_files < 1 or max_files > 100000:
        raise ValueError("max_files must be between 1 and 100000")
    indexed = []
    for current, directories, filenames in os.walk(base, followlinks=False):
        directories[:] = sorted(d for d in directories if not (Path(current) / d).is_symlink())
        for filename in sorted(filenames):
            candidate = Path(current) / filename
            if candidate.is_symlink() or not candidate.is_file():
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
