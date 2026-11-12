import hashlib
import tempfile
import unittest
from pathlib import Path

from compresso_cas.indexer import index_tree
from compresso_cas.registry import CasRegistry


class CasRegistryTests(unittest.TestCase):
    def test_ingest_creates_content_hash_uuid_and_alias(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "libsample.so"
            source.write_bytes(b"ELF-test-content")
            registry = CasRegistry(root / "cas")
            record = registry.ingest(source)
            self.assertEqual(record["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(registry.resolve(source)["uuid"], record["uuid"])
            self.assertEqual(registry.resolve(source)["state"], "verified")

    def test_audit_quarantines_corrupt_blob_and_reports_cpu_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "binary"
            source.write_bytes(b"original")
            registry = CasRegistry(root / "cas")
            registry.ingest(source)
            blob = Path(registry.resolve(source)["path"])
            blob.chmod(0o644)
            blob.write_bytes(b"tampered")
            result = registry.audit()
            self.assertEqual(result[0]["state"], "corrupt")
            self.assertEqual(result[0]["fallback"], "cpu")
            self.assertFalse(blob.exists())
            self.assertTrue((root / "cas" / "quarantine").is_dir())

    def test_symlink_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.write_text("safe")
            link = root / "link"
            link.symlink_to(source)
            registry = CasRegistry(root / "cas")
            with self.assertRaises(ValueError):
                registry.ingest(link)

    def test_indexer_only_snapshots_elf_and_never_modifies_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            elf = root / "app"
            elf.write_bytes(b"\x7fELF" + b"payload")
            plain = root / "notes.txt"
            plain.write_text("not an executable")
            before = elf.read_bytes()
            registry = CasRegistry(root / "cas")
            result = index_tree(root, registry)
            self.assertEqual(len(result), 1)
            self.assertFalse(result[0]["binary_modified"])
            self.assertEqual(result[0]["translation"], "indexed_only")
            self.assertEqual(elf.read_bytes(), before)
            self.assertIsNone(registry.resolve(plain))


if __name__ == "__main__":
    unittest.main()
