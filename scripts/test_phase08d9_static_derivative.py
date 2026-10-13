"""Focused negative controls using inert source copies; no upstream execution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase08d9_static as static
import materialize_phase08d9_provider_boundary as materializer
import verify_phase08d9_provider_boundary as verifier

CONTEXT = None


class StaticControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.indexed, cls.metadata, cls.receipts = static.inputs(CONTEXT)
        cls.derivative = {p: materializer.transform(data) if p in static.MODIFIED else data for p, data in cls.original.items()}
        cls.manifest = materializer.manifest(cls.original, cls.derivative, cls.indexed, cls.metadata, cls.receipts)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="negative-", dir=static.ROOT / ".local/phase08d9")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def args(self, **kwargs):
        return SimpleNamespace(**(vars(CONTEXT) | kwargs))

    def fixture(self):
        out = self.directory / "derivative"
        for p, data in self.derivative.items():
            path = out / "source" / p
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (out / "receipt.json").write_bytes(static.canonical(self.manifest))
        (out / "bootstrap.patch").write_bytes(materializer.patch(self.original, self.derivative))
        return self.args(derivative=out, manifest=out / "receipt.json")

    def rejected_tree(self, mutate):
        args = self.fixture()
        mutate(args.derivative)
        with self.assertRaises((ValueError, FileNotFoundError)):
            verifier.verify_tree(args)

    def frontier_fixture(self):
        out = self.directory / "frontier"
        shutil.copytree(CONTEXT.source_frontier / "hindsight-api-slim", out / "hindsight-api-slim")
        return out

    def test_positive_independent_static_verification(self):
        verifier.verify_tree(self.fixture())

    def test_original_source_tamper(self):
        out = self.frontier_fixture()
        path = out / static.MODIFIED[0]
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            static.inputs(self.args(source_frontier=out))

    def test_original_eol_drift(self):
        out = self.frontier_fixture()
        path = out / static.MODIFIED[0]
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            static.inputs(self.args(source_frontier=out))

    def test_missing_source_input(self):
        out = self.frontier_fixture()
        (out / static.MODIFIED[0]).unlink()
        with self.assertRaisesRegex(ValueError, "source inputs"):
            static.inputs(self.args(source_frontier=out))

    def test_unexpected_source_input(self):
        out = self.frontier_fixture()
        (out / "hindsight-api-slim/hindsight_api/extra.py").write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "source inputs"):
            static.inputs(self.args(source_frontier=out))

    def test_original_symlink_substitution(self):
        out = self.frontier_fixture()
        path = out / static.MODIFIED[0]
        path.unlink()
        path.symlink_to(CONTEXT.source_frontier / static.MODIFIED[0])
        with self.assertRaisesRegex(ValueError, "symlink"):
            static.inputs(self.args(source_frontier=out))

    def test_unexpected_cache_input(self):
        out = self.directory / "cache"
        shutil.copytree(CONTEXT.source_cache, out)
        (out / "unapproved_helper.py").write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "cache source inputs"):
            static.inputs(self.args(source_cache=out))

    def test_modified_dependency_metadata(self):
        out = self.directory / "metadata"
        out.mkdir()
        for name, data in self.metadata.items():
            (out / name).write_bytes(data + (b"\n" if name == "uv.lock" else b""))
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            static.inputs(self.args(metadata_root=out))

    def test_wrong_pinned_tree(self):
        out = self.directory / "tree.json"
        out.write_bytes(CONTEXT.pinned_tree.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "tree response mismatch"):
            static.inputs(self.args(pinned_tree=out))

    def test_tampered_immutable_source_receipt(self):
        root = self.directory / "repo"
        (root / "manifests").mkdir(parents=True)
        for name in static.RECEIPTS:
            data = (static.ROOT / "manifests" / name).read_bytes()
            (root / "manifests" / name).write_bytes(data + (b"\n" if "adaptive-source-closure" in name else b""))
        with patch.object(static, "ROOT", root), self.assertRaisesRegex(ValueError, "immutable receipt changed"):
            static.evidence()

    def test_tampered_dependency_artifact(self):
        read = static.regular
        def changed(path):
            data = read(path)
            return data + b"tamper" if path.suffix == ".whl" else data
        with patch.object(static, "regular", changed), self.assertRaisesRegex(ValueError, "artifact changed"):
            static.closure(self.derivative, self.indexed, self.metadata, self.receipts)

    def test_forged_dependency_closure(self):
        def mutate(out):
            forged = json.loads((out / "receipt.json").read_bytes())
            forged["included_source_closure"]["packages"]["package_versions"].pop("sqlalchemy")
            (out / "receipt.json").write_bytes(static.canonical(forged))
        self.rejected_tree(mutate)

    def test_missing_derivative_helper(self):
        self.rejected_tree(lambda out: (out / "source" / (static.PREFIX + "config.py")).unlink())

    def test_unexpected_derivative_source(self):
        self.rejected_tree(lambda out: (out / "source/extra.py").write_bytes(b""))

    def test_unexpected_empty_directory(self):
        self.rejected_tree(lambda out: (out / "fake-package").mkdir())

    def test_derivative_symlink_substitution(self):
        def mutate(out):
            p = out / "source" / (static.PREFIX + "config.py")
            p.unlink()
            p.symlink_to(CONTEXT.source_cache / "config.py")
        self.rejected_tree(mutate)

    def test_out_of_scope_provider_patch(self):
        self.rejected_tree(lambda out: (out / "source" / (static.PREFIX + "engine/providers/openai_compatible_llm.py")).write_bytes(b"# replaced provider\n"))

    def test_out_of_scope_root_patch_with_forged_identity(self):
        def mutate(out):
            p = static.PREFIX + "__init__.py"
            new = self.derivative[p] + b"\n# unapproved root patch\n"
            (out / "source" / p).write_bytes(new)
            forged = json.loads((out / "receipt.json").read_bytes())
            row = next(r for r in forged["files"] if r["original_path"] == p)
            row["derivative"] = static.identities(new)
            row["classification"] = "MODIFIED_BOOTSTRAP"
            (out / "receipt.json").write_bytes(static.canonical(forged))
        self.rejected_tree(mutate)

    def test_changed_public_export(self):
        old = self.original[static.MODIFIED[0]]
        altered = self.derivative[static.MODIFIED[0]].replace(b"'MemoryEngine':", b"'WrongEngine':")
        with self.assertRaisesRegex(ValueError, "initializer syntax"):
            verifier.verify_initializer(old, altered)

    def test_changed_symbol_target(self):
        old = self.original[static.MODIFIED[0]]
        altered = self.derivative[static.MODIFIED[0]].replace(b"('.memory_engine', 'MemoryEngine')", b"('.embeddings', 'MemoryEngine')")
        with self.assertRaisesRegex(ValueError, "initializer syntax"):
            verifier.verify_initializer(old, altered)

    def test_changed_all_order(self):
        old = self.original[static.MODIFIED[2]]
        altered = self.derivative[static.MODIFIED[2]].replace(b'__all__ = ["WorkerPoller"]', b'__all__ = ["Other"]')
        with self.assertRaisesRegex(ValueError, "initializer syntax"):
            verifier.verify_initializer(old, altered)

    def test_swallowed_target_exception(self):
        old = self.original[static.MODIFIED[2]]
        altered = self.derivative[static.MODIFIED[2]].replace(b"except KeyError:", b"except Exception:")
        with self.assertRaisesRegex(ValueError, "initializer syntax"):
            verifier.verify_initializer(old, altered)

    def test_eager_excluded_implementation(self):
        old = self.original[static.MODIFIED[0]]
        altered = self.derivative[static.MODIFIED[0]] + b"\nfrom .memory_engine import MemoryEngine\n"
        with self.assertRaisesRegex(ValueError, "initializer syntax"):
            verifier.verify_initializer(old, altered)
        source = self.derivative | {static.MODIFIED[0]: altered}
        with self.assertRaisesRegex(ValueError, "excluded implementation"):
            static.closure(source, self.indexed, self.metadata, self.receipts)

    def test_extra_initializer_execution(self):
        old = self.original[static.MODIFIED[2]]
        altered = self.derivative[static.MODIFIED[2]] + b"\nprint('unapproved effect')\n"
        with self.assertRaisesRegex(ValueError, "initializer syntax"):
            verifier.verify_initializer(old, altered)

    def test_patch_tamper_and_out_of_scope_hunk(self):
        self.rejected_tree(lambda out: (out / "bootstrap.patch").write_bytes(b"--- a/hindsight-api-slim/hindsight_api/config.py\n+++ b/hindsight-api-slim/hindsight_api/config.py\n"))

    def test_manifest_forgery(self):
        def mutate(out):
            forged = json.loads((out / "receipt.json").read_bytes())
            forged["UNMODIFIED_HINDSIGHT_RUNTIME"] = True
            (out / "receipt.json").write_bytes(static.canonical(forged))
        self.rejected_tree(mutate)

    def test_existing_output_rejected_without_overwrite(self):
        out = self.directory / "output"
        out.mkdir()
        (out / "receipt.json").write_bytes(b"immutable receipt\n")
        with self.assertRaises(FileExistsError):
            materializer.materialize(self.args(output=out, publish_manifest=None))
        self.assertEqual((out / "receipt.json").read_bytes(), b"immutable receipt\n")

    def test_existing_published_manifest_rejected_before_creation(self):
        published = self.directory / "published.json"
        published.write_bytes(b"immutable published\n")
        out = self.directory / "new-output"
        with self.assertRaises(FileExistsError):
            materializer.materialize(self.args(output=out, publish_manifest=published))
        self.assertFalse(out.exists())
        self.assertEqual(published.read_bytes(), b"immutable published\n")

    def test_outside_and_traversal_output_rejected(self):
        for out in (self.directory / ".." / "escape", static.ROOT / "unignored-output"):
            with self.assertRaises(ValueError):
                static.ignored_output(out)

    def test_git_ssh_and_rewrite_targets_rejected(self):
        for url in ("git@github.com:IanJ332/Memo.git", "ssh://git@github.com/IanJ332/Memo.git", "file:///tmp/repo", "https://user:secret@github.com/repo"):
            with self.assertRaises(ValueError):
                static.https_url(url)
        static.https_url("https://github.com/IanJ332/Memo.git")

    def test_guard_rejects_sdk_and_network_before_execution(self):
        with self.assertRaisesRegex(RuntimeError, "forbidden"):
            sys.audit("import", "openai", None, [], [], [])
        with self.assertRaisesRegex(RuntimeError, "forbidden"):
            sys.audit("socket.getaddrinfo", "invalid.test", 443, 0, 0, 0)


def main():
    global CONTEXT
    static.guard()
    parser = argparse.ArgumentParser(description=__doc__)
    static.arguments(parser)
    parser.add_argument("--receipt-output", type=Path, required=True)
    CONTEXT = parser.parse_args()
    if CONTEXT.receipt_output.exists():
        raise FileExistsError("STOP: test receipt already exists")
    (static.ROOT / ".local/phase08d9").mkdir(parents=True, exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StaticControls)
    names = [test.id().rsplit(".", 1)[-1] for test in suite]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {"phase": "08D-9_STAGE_1", "tests": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "successful": result.wasSuccessful(),
               "cases": names,
               "test_script": static.identities(Path(__file__).read_bytes()),
               "native_sdk_imports_calls": 0, "claim": "STATIC_NEGATIVE_CONTROLS_ONLY"}
    with CONTEXT.receipt_output.open("xb") as stream:
        stream.write(static.canonical(receipt))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
