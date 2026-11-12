"""Immutable SHA-256 CAS store with SQLite aliases and background audit."""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List


class CasRegistry:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.blobs = self.root / "sha256"
        self.quarantine = self.root / "quarantine"
        self.database = self.root / "cas_registry.db"
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.quarantine.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS blocks (
                    sha256 TEXT PRIMARY KEY,
                    uuid TEXT NOT NULL UNIQUE,
                    size_bytes INTEGER NOT NULL,
                    relative_path TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'verified'
                );
                CREATE TABLE IF NOT EXISTS aliases (
                    original_path TEXT PRIMARY KEY,
                    sha256 TEXT NOT NULL REFERENCES blocks(sha256)
                );
            """)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.database)
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _hash(path: Path) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
        return digest.hexdigest(), size

    def ingest(self, source: str | Path) -> Dict[str, object]:
        source_path = Path(source)
        if source_path.is_symlink() or not source_path.is_file():
            raise ValueError("source must be a regular, non-symlink file")
        digest, size = self._hash(source_path)
        relative = Path("sha256") / digest[:2] / digest
        destination = self.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            fd, temporary = tempfile.mkstemp(prefix=".incoming-", dir=destination.parent)
            try:
                with os.fdopen(fd, "wb") as output, source_path.open("rb") as input_stream:
                    shutil.copyfileobj(input_stream, output)
                    output.flush()
                    os.fsync(output.fileno())
                copied_hash, copied_size = self._hash(Path(temporary))
                if copied_hash != digest or copied_size != size:
                    raise RuntimeError("source changed while CAS snapshot was being created")
                os.chmod(temporary, 0o444)
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        block_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "sha256:" + digest))
        with self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO blocks(sha256,uuid,size_bytes,relative_path,state) VALUES(?,?,?,?,?)",
                (digest, block_uuid, size, str(relative), "verified"),
            )
            db.execute(
                "INSERT INTO aliases(original_path,sha256) VALUES(?,?) "
                "ON CONFLICT(original_path) DO UPDATE SET sha256=excluded.sha256",
                (str(source_path.resolve()), digest),
            )
        return {"sha256": digest, "uuid": block_uuid, "size_bytes": size,
                "uri": "cas://sha256/" + digest}

    def resolve(self, original_path: str | Path) -> Dict[str, object] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT b.sha256,b.uuid,b.size_bytes,b.relative_path,b.state "
                "FROM aliases a JOIN blocks b USING(sha256) WHERE a.original_path=?",
                (str(Path(original_path).resolve()),),
            ).fetchone()
        if row is None:
            return None
        return {"sha256": row[0], "uuid": row[1], "size_bytes": row[2],
                "path": str(self.root / row[3]), "state": row[4]}

    def audit(self) -> List[Dict[str, object]]:
        with self._connect() as db:
            rows = db.execute("SELECT sha256,relative_path FROM blocks ORDER BY sha256").fetchall()
        results = []
        for digest, relative in rows:
            blob = self.root / relative
            state = "verified"
            if not blob.is_file():
                state = "missing"
            else:
                actual, _ = self._hash(blob)
                if actual != digest:
                    state = "corrupt"
                    quarantine_path = self.quarantine / (digest + ".corrupt")
                    if quarantine_path.exists():
                        quarantine_path = self.quarantine / (digest + "." + uuid.uuid4().hex)
                    os.replace(blob, quarantine_path)
            with self._connect() as db:
                db.execute("UPDATE blocks SET state=? WHERE sha256=?", (state, digest))
            results.append({"sha256": digest, "state": state,
                            "fallback": "cpu" if state != "verified" else "none"})
        return results
