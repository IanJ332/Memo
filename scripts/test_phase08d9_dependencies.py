"""Deterministic Stage 2 integrity/rejection controls; no network or SDK imports."""
from __future__ import annotations

import argparse
import base64
import copy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_phase08d9_provider_boundary as prep


def fixture(changes=None, extra=None, duplicate=False):
    files = {"example/__init__.py": b"# inert fixture; never imported\n",
             "example-1.0.dist-info/METADATA": b"Metadata-Version: 2.3\nName: example\nVersion: 1.0\nRequires-Python: >=3.9\n",
             "example-1.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nGenerator: deterministic-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n"}
    files.update(changes or {})
    files.update(extra or {})
    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for name, data in sorted(files.items()):
        digest = base64.urlsafe_b64encode(prep.hashlib.sha256(data).digest()).rstrip(b"=").decode()
        writer.writerow([name, "sha256=" + digest, len(data)])
    writer.writerow(["example-1.0.dist-info/RECORD", "", ""])
    files["example-1.0.dist-info/RECORD"] = record.getvalue().encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            z.writestr(info, data)
        if duplicate:
            # Deliberate duplicate bypass input; zipfile warns, verifier rejects.
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr("example/__init__.py", b"duplicate")
    data = buffer.getvalue()
    row = {"name": "example", "version": "1.0", "filename": "example-1.0-py3-none-any.whl",
           "url": "https://files.pythonhosted.org/packages/test/example-1.0-py3-none-any.whl",
           "sha256": prep.sha(data), "bytes": len(data), "tags": ["py3-none-any"]}
    return data, row


class Integrity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=prep.AREA)
        self.folder = Path(self.temp.name)
        self.data, self.row = fixture()
        self.plan = {"target": {"compatible_tags": ["py3-none-any"]}}
        self.path = self.folder / self.row["filename"]
        self.path.write_bytes(self.data)

    def tearDown(self):
        self.temp.cleanup()

    def reject(self, operation):
        with self.assertRaises((ValueError, FileExistsError, RuntimeError)):
            operation()

    def wheel(self):
        return prep.verify_wheel(self.path, self.row, self.plan)

    def rebuilt(self, **kwargs):
        self.data, self.row = fixture(**kwargs)
        self.path.write_bytes(self.data)

    def test_valid_record_zip_metadata(self):
        self.assertEqual(self.wheel()["wheel_record_files_verified"], 3)

    def test_hash_tamper(self):
        self.path.write_bytes(self.data[:-1] + bytes([self.data[-1] ^ 1]))
        self.reject(self.wheel)

    def test_size_tamper(self):
        self.row["bytes"] += 1
        self.reject(self.wheel)

    def test_missing_hash(self):
        self.row["sha256"] = None
        self.reject(lambda: prep.artifact_ok(self.row, ["py3-none-any"]))

    def test_wrong_filename_version(self):
        self.row["filename"] = "example-2.0-py3-none-any.whl"
        self.reject(lambda: prep.artifact_ok(self.row, ["py3-none-any"]))

    def test_incompatible_tags(self):
        self.reject(lambda: prep.artifact_ok(self.row, ["cp311-cp311-win_amd64"]))

    def test_non_https_url(self):
        self.row["url"] = self.row["url"].replace("https:", "http:")
        self.reject(lambda: prep.url_ok(self.row))

    def test_wrong_host_url(self):
        self.row["url"] = self.row["url"].replace("files.pythonhosted.org", "example.test")
        self.reject(lambda: prep.url_ok(self.row))

    def test_credentials_url(self):
        self.row["url"] = self.row["url"].replace("https://", "https://secret@")
        self.reject(lambda: prep.url_ok(self.row))

    def test_query_url(self):
        self.row["url"] += "?alternate=1"
        self.reject(lambda: prep.url_ok(self.row))

    def test_wheel_metadata_wrong_version(self):
        self.rebuilt(changes={"example-1.0.dist-info/METADATA": b"Name: example\nVersion: 2.0\n"})
        self.reject(self.wheel)

    def test_wheel_metadata_incompatible_python(self):
        self.rebuilt(changes={"example-1.0.dist-info/METADATA": b"Name: example\nVersion: 1.0\nRequires-Python: >=3.13\n"})
        self.reject(self.wheel)

    def test_wheel_tag_metadata_drift(self):
        self.rebuilt(changes={"example-1.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py2-none-any\n"})
        self.reject(self.wheel)

    def test_zip_traversal(self):
        self.rebuilt(extra={"../../escape.py": b"escape"})
        self.reject(self.wheel)

    def test_duplicate_zip_path(self):
        self.rebuilt(duplicate=True)
        self.reject(self.wheel)

    def test_executable_pth(self):
        self.rebuilt(extra={"execute.pth": b"import example\n"})
        self.reject(self.wheel)

    def test_header_relocation_stops_current_verifier(self):
        # Exposes the actual greenlet STOP limitation for independent review.
        # This header is inert; the current verifier lacks relocation mapping.
        self.rebuilt(extra={"example-1.0.data/headers/example.h": b"/* inert header */\n"})
        self.reject(self.wheel)

    def test_extra_distribution_owner(self):
        self.rebuilt(extra={"other-1.0.dist-info/METADATA": b"Name: other\nVersion: 1.0\n"})
        self.reject(self.wheel)

    def test_symlink_input(self):
        link = self.folder / "link.whl"
        link.symlink_to(self.path)
        self.reject(lambda: prep.verify_wheel(link, self.row, self.plan))

    def test_record_hash_mismatch(self):
        self.reject(lambda: prep.check_record(b"entry,sha256=invalid,3\n", lambda n: b"abc"))

    def test_record_omitted_member(self):
        self.reject(lambda: prep.check_record(b"a.dist-info/RECORD,,\n", lambda n: b"", ["a.dist-info/RECORD", "missing"]))

    def test_record_unhashed_file(self):
        self.reject(lambda: prep.check_record(b"code.py,,\n", lambda n: b"code"))

    def test_record_duplicate_ownership(self):
        self.reject(lambda: prep.check_record(b"a.dist-info/RECORD,,\na.dist-info/RECORD,,\n", lambda n: b""))

    def test_installed_record_escape(self):
        with patch.object(prep, "RUNTIME", self.folder):
            self.reject(lambda: prep.installed_path(self.folder, "../../outside"))

    def test_frozen_source_manifest_change(self):
        bad = self.folder / "bad.json"
        bad.write_bytes(prep.regular(prep.SOURCE) + b" ")
        self.reject(lambda: prep.load_source(bad))

    def test_frozen_plan_change(self):
        plan = prep.load_plan()
        plan["artifacts"][0]["version"] = "99.0"
        altered = prep.canonical(plan)
        original_regular = prep.regular
        def read(path):
            return altered if Path(path) == prep.AREA / "acquisition-plan.json" else original_regular(path)
        with patch.object(prep, "regular", read):
            self.reject(prep.load_plan)

    def test_duplicate_dependency_set(self):
        source = prep.load_source()
        source["included_source_closure"]["packages"]["artifact_plan"].append(
            source["included_source_closure"]["packages"]["artifact_plan"][0])
        self.reject(lambda: prep.build_plan(source))

    def test_added_metadata_dependency(self):
        plan = {"artifacts": [self.row], "dependency_edges": [], "metadata_marker_environment": {"extra": ""}}
        wheel = {"name": "example", "version": "1.0", "requires_dist": ["unexpected>=1"]}
        self.reject(lambda: prep.dependencies([wheel], plan))

    def test_incompatible_dependency_version(self):
        plan = {"artifacts": [self.row], "dependency_edges": [], "metadata_marker_environment": {"extra": ""}}
        wheel = {"name": "example", "version": "1.0", "requires_dist": ["example>=2"]}
        self.reject(lambda: prep.dependencies([wheel], plan))

    def test_marker_selection(self):
        plan = {"artifacts": [self.row], "dependency_edges": [], "metadata_marker_environment": {"extra": "", "sys_platform": "darwin"}}
        wheel = {"name": "example", "version": "1.0", "requires_dist": ["unexpected; sys_platform == 'win32'"]}
        self.assertFalse(prep.dependencies([wheel], plan)["marker_selections"][0]["selected"])

    def downloaded(self, status="200", fail=False, collision=False):
        calls = []
        log = self.folder / "requests.jsonl"
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            self.assertEqual(kwargs["env"], {"PATH": "/usr/bin:/bin"})
            Path(command[command.index("--output") + 1]).write_bytes(self.data)
            if fail:
                raise subprocess.TimeoutExpired(command, 65)
            return subprocess.CompletedProcess(command, 0,
                f"{status}\n0\n0\n{self.row['url']}\n{len(self.data)}\n", "")
        destination = self.folder / "downloads"
        destination.mkdir()
        if collision:
            (destination / self.row["filename"]).write_bytes(b"preserve")
        with log.open("xb") as stream:
            operation = lambda: prep.download(self.row, self.plan, destination, stream, 1, 0, runner)
            if status != "200" or fail or collision:
                self.reject(operation) if not fail else self.assertRaises(subprocess.TimeoutExpired, operation)
            else:
                operation()
        events = [json.loads(line) for line in log.read_bytes().splitlines()]
        self.assertEqual(len(calls), 1)
        self.assertEqual(events[0]["event"], "REQUEST_BEGIN")
        return events, destination

    def test_one_controlled_success(self):
        events, _ = self.downloaded()
        self.assertEqual([e["event"] for e in events], ["REQUEST_BEGIN", "REQUEST_RESULT", "VERIFIED"])

    def test_redirect_rejected_logged(self):
        events, _ = self.downloaded(status="302")
        self.assertEqual(events[-1]["event"], "STOP")

    def test_timeout_logged_no_retry(self):
        events, _ = self.downloaded(fail=True)
        self.assertEqual(events[-1]["event"], "STOP")

    def test_promotion_collision_preserved(self):
        _, destination = self.downloaded(collision=True)
        self.assertEqual((destination / self.row["filename"]).read_bytes(), b"preserve")

    def test_request_budget_before_request(self):
        self.reject(lambda: prep.download(self.row, self.plan, self.folder, io.BytesIO(), 23, 0))

    def test_byte_budget_before_request(self):
        self.reject(lambda: prep.download(self.row, self.plan, self.folder, io.BytesIO(), 1, prep.LIMIT_BYTES))

    def test_receipt_overwrite_rejected(self):
        receipt = self.folder / "receipt.json"
        prep.write_new(receipt, b"original")
        self.reject(lambda: prep.write_new(receipt, b"replacement"))
        self.assertEqual(receipt.read_bytes(), b"original")

    def test_native_sdk_import_denied_before_execution(self):
        for name in sorted(prep.BANNED):
            with self.assertRaises(RuntimeError):
                __import__(name)

    def test_socket_dns_denied(self):
        import socket
        for operation in (lambda: socket.socket(), lambda: socket.getaddrinfo("fixture.test", 443)):
            with self.assertRaises(RuntimeError):
                operation()


def main():
    prep.guard()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Integrity)
    names = [test.id() for test in suite]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {"phase": "08D-9_STAGE_2", "evidence_class": "DETERMINISTIC_INTEGRITY_CONTROLS",
        "tests": result.testsRun, "failures": [(t.id(), text) for t, text in result.failures],
        "errors": [(t.id(), text) for t, text in result.errors], "cases": names,
        "native_sdk_imports": 0, "real_download_requests": 0, "external_network": "OS_DENIED",
        "test_script_sha256": prep.sha(prep.regular(Path(__file__))),
        "preparation_script_sha256": prep.sha(prep.regular(Path(prep.__file__)))}
    prep.write_new(args.receipt, prep.canonical(receipt))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
