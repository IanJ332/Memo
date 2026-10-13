"""Original 39 controls plus exact header/ownership and ledger continuation cases."""
from __future__ import annotations

import argparse
import copy
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_phase08d9_provider_boundary as p
import continue_phase08d9_dependencies as c
import test_phase08d9_dependencies as existing


class Continuation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=c.C)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.runtime = self.folder / ".venv"
        self.runtime.mkdir()
        self.patcher = patch.object(p, "RUNTIME", self.runtime)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        # Frozen production plan is read before replacing runtime paths in it.
        self.plan = json.loads(p.regular(p.AREA / "acquisition-plan.json"))
        self.row = next(a for a in self.plan["artifacts"] if a["name"] == "greenlet")
        self.wheel = p.AREA / "downloads" / (self.row["filename"] + ".part")
        self.scheme = p.installer_scheme(self.runtime, "greenlet")
        self.site = Path(self.scheme["platlib"])
        self.archive = zipfile.ZipFile(self.wheel)
        self.addCleanup(self.archive.close)
        self.mapping = p.member_destinations(self.archive, self.row, self.scheme, self.runtime)
        record_name = next(n for n in self.mapping if n.endswith(".dist-info/RECORD"))
        source_rows = list(csv.reader(io.StringIO(self.archive.read(record_name).decode())))
        self.rows = []
        for source, value, size in source_rows:
            target = self.mapping[source]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.archive.read(source))
            self.rows.append([p.os.path.relpath(target, self.site), value, size])
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="\n").writerows(self.rows)
        self.mapping[record_name].write_text(buffer.getvalue())
        self.header = self.mapping[p.GREENLET_HEADER]

    def verify(self, rows=None, scheme=None, archive=None):
        return p.check_installed_members(archive or self.archive, self.row, scheme or self.scheme,
                                         self.site, self.runtime, self.rows if rows is None else rows)

    def reject(self, operation):
        with self.assertRaises((ValueError, RuntimeError, FileNotFoundError)):
            operation()

    def modified_archive(self, name, data=b"unexpected", symlink=False):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            for info in self.archive.infolist():
                z.writestr(info, self.archive.read(info.filename))
            info = zipfile.ZipInfo(name)
            if symlink:
                info.create_system = 3
                info.external_attr = (0o120777 << 16)
            z.writestr(info, data)
        archive = zipfile.ZipFile(io.BytesIO(buffer.getvalue()))
        self.addCleanup(archive.close)
        return archive

    def test_exact_approved_wheel_positive(self):
        self.assertEqual(p.verify_wheel(self.wheel, self.row, self.plan)["approved_header_relocation"], p.GREENLET_HEADER)

    def test_header_mapping_uses_installer_scheme(self):
        mapped, relocations = self.verify()
        self.assertEqual(self.header, Path(self.scheme["headers"]) / "greenlet.h")
        self.assertNotEqual(self.header, self.site / p.GREENLET_HEADER)
        self.assertEqual(len(mapped), len(self.rows))
        self.assertEqual(relocations[0]["installed_record_path"], p.os.path.relpath(self.header, self.site))

    def test_header_record_hash_and_bytes_positive(self):
        record = io.StringIO()
        csv.writer(record).writerows(self.rows)
        count, _ = p.check_record(record.getvalue().encode(), lambda name: p.regular(p.installed_path(self.site, name)))
        self.assertEqual(count, 94)
        self.assertEqual(self.header.read_bytes(), self.archive.read(p.GREENLET_HEADER))
        self.verify()

    def test_header_byte_tampering(self):
        data = self.header.read_bytes()
        self.header.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        self.reject(self.verify)

    def test_header_record_hash_mismatch(self):
        rows = copy.deepcopy(self.rows)
        next(row for row in rows if row[0] == p.os.path.relpath(self.header, self.site))[1] = "sha256=wrong"
        self.reject(lambda: self.verify(rows=rows))

    def test_header_record_size_mismatch(self):
        rows = copy.deepcopy(self.rows)
        next(row for row in rows if row[0] == p.os.path.relpath(self.header, self.site))[2] = "0"
        self.reject(lambda: self.verify(rows=rows))

    def test_missing_installed_header(self):
        self.header.unlink()
        self.reject(self.verify)

    def test_missing_header_record_ownership(self):
        rows = [r for r in self.rows if r[0] != p.os.path.relpath(self.header, self.site)]
        self.reject(lambda: self.verify(rows=rows))

    def test_duplicate_header_record_ownership(self):
        rows = self.rows + [next(r for r in self.rows if r[0] == p.os.path.relpath(self.header, self.site))]
        self.reject(lambda: self.verify(rows=rows))

    def test_cross_distribution_duplicate_destination_ownership(self):
        owners = {self.header: "unrelated-distribution"}
        self.reject(lambda: p.claim_installed_ownership(self.site, self.rows, "greenlet", owners))

    def test_unexpected_data_header(self):
        z = self.modified_archive("greenlet-3.2.4.data/headers/unreviewed.h")
        self.reject(lambda: self.verify(archive=z))

    def test_relocation_into_scripts(self):
        z = self.modified_archive("greenlet-3.2.4.data/scripts/tool")
        self.reject(lambda: self.verify(archive=z))

    def test_relocation_into_binaries(self):
        z = self.modified_archive("greenlet-3.2.4.data/platlib/native.so")
        self.reject(lambda: self.verify(archive=z))

    def test_relocation_into_unrelated_destination(self):
        scheme = {**self.scheme, "headers": str(self.runtime / "unrelated")}
        self.reject(lambda: self.verify(scheme=scheme))

    def test_scheme_headers_into_bin(self):
        self.reject(lambda: self.verify(scheme={**self.scheme, "headers": self.scheme["scripts"]}))

    def test_absolute_destination_escape(self):
        self.reject(lambda: p.safe_destination(Path("/private/tmp/unrelated.h"), self.runtime))

    def test_absolute_archive_source(self):
        z = self.modified_archive("/absolute/header.h")
        self.reject(lambda: self.verify(archive=z))

    def test_path_traversal(self):
        z = self.modified_archive("greenlet-3.2.4.data/headers/../../bin/tool")
        self.reject(lambda: self.verify(archive=z))

    def test_header_symlink(self):
        other = self.folder / "other.h"
        other.write_bytes(self.header.read_bytes())
        self.header.unlink()
        self.header.symlink_to(other)
        self.reject(self.verify)

    def test_header_parent_symlink(self):
        parent = self.header.parent
        self.header.unlink()
        parent.rmdir()
        parent.symlink_to(self.folder, target_is_directory=True)
        self.reject(self.verify)

    def test_archive_symlink(self):
        z = self.modified_archive("greenlet/linked.h", symlink=True)
        self.reject(lambda: self.verify(archive=z))

    def test_executable_pth_content(self):
        z = self.modified_archive("activate.pth", b"import greenlet\n")
        self.reject(lambda: self.verify(archive=z))

    def test_same_header_under_substituted_artifact_hash(self):
        row = {**self.row, "sha256": "0" * 64}
        self.reject(lambda: p.member_destinations(self.archive, row, self.scheme, self.runtime))

    def test_installed_archive_path_is_not_header_record_path(self):
        rows = copy.deepcopy(self.rows)
        next(r for r in rows if r[0] == p.os.path.relpath(self.header, self.site))[0] = p.GREENLET_HEADER
        self.reject(lambda: self.verify(rows=rows))

    def test_original_ledger_positive(self):
        events = [json.loads(line) for line in p.regular(p.AREA / "requests.jsonl").splitlines()]
        c.validate_original_ledger(events, self.plan)

    def test_original_ledger_replayed_request(self):
        events = [json.loads(line) for line in p.regular(p.AREA / "requests.jsonl").splitlines()]
        events[15]["request"] = 5
        self.reject(lambda: c.validate_original_ledger(events, self.plan))

    def test_original_ledger_altered_artifact(self):
        events = [json.loads(line) for line in p.regular(p.AREA / "requests.jsonl").splitlines()]
        events[0]["url"] += "?alternate=1"
        self.reject(lambda: c.validate_original_ledger(events, self.plan))

    def test_original_failure_not_reinterpreted(self):
        events = [json.loads(line) for line in p.regular(p.AREA / "requests.jsonl").splitlines()]
        events[-1]["event"] = "VERIFIED"
        self.reject(lambda: c.validate_original_ledger(events, self.plan))

    def test_snapshot_changed_rejected(self):
        read = p.regular
        def altered(path):
            data = read(path)
            return data + b" " if Path(path) == c.C / "existing-evidence.json" else data
        with patch.object(p, "regular", altered):
            self.reject(lambda: c.historical_evidence(self.plan))

    def continuation_events(self):
        header = {"event": "CONTINUATION_BEGIN", "original_ledger_sha256": "original", "frozen_plan_sha256": c.PLAN_SHA}
        events = [header]
        for index, a in enumerate(c.download_rows(self.plan)[6:], 7):
            events.extend([{"event": "REQUEST_BEGIN", "request": index, "name": a["name"], "url": a["url"],
                            "expected_bytes": a["bytes"], "expected_sha256": a["sha256"]},
                {"event": "REQUEST_RESULT", "request": index, "exit_code": 0, "stderr": "", "observed_bytes": a["bytes"],
                    "observed_sha256": a["sha256"], "curl_fields": ["200", "0", "0", a["url"], str(a["bytes"])]},
                {"event": "VERIFIED", "request": index, "name": a["name"], "filename": a["filename"],
                    "sha256": a["sha256"], "bytes": a["bytes"]}])
        return header, events

    def test_continuation_accounting_positive(self):
        header, events = self.continuation_events()
        with patch.object(c, "ledger_header", return_value=header):
            c.validate_continuation(self.plan, events)

    def test_continuation_link_altered(self):
        header, events = self.continuation_events()
        expected = copy.deepcopy(header)
        events[0]["original_ledger_sha256"] = "different"
        with patch.object(c, "ledger_header", return_value=expected):
            self.reject(lambda: c.validate_continuation(self.plan, events))

    def test_continuation_request_replayed(self):
        header, events = self.continuation_events()
        events[1]["request"] = 6
        with patch.object(c, "ledger_header", return_value=header):
            self.reject(lambda: c.validate_continuation(self.plan, events))

    def test_continuation_extra_request(self):
        header, events = self.continuation_events()
        events.extend(copy.deepcopy(events[-3:]))
        with patch.object(c, "ledger_header", return_value=header):
            self.reject(lambda: c.validate_continuation(self.plan, events))

    def test_continuation_byte_accounting_altered(self):
        header, events = self.continuation_events()
        events[2]["observed_bytes"] += 1
        with patch.object(c, "ledger_header", return_value=header):
            self.reject(lambda: c.validate_continuation(self.plan, events))

    def test_offline_child_inherits_kernel_denial(self):
        log = self.folder / "child-policy.json"
        code = ("import ctypes,os,json; lib=ctypes.CDLL('/usr/lib/libsandbox.1.dylib'); "
                "check=lib.sandbox_check; check.restype=ctypes.c_int; "
                "print(json.dumps({op:check(ctypes.c_int(os.getpid()),ctypes.c_char_p(op.encode()),ctypes.c_int(0)) "
                "for op in ('network-outbound','network-inbound')}))")
        result = p.offline_run([sys.executable, "-I", "-B", "-c", code], log)
        self.assertEqual(set(json.loads(result.stdout).values()), {1})
        self.assertEqual(json.loads(log.read_bytes())["network_denial_mode"], "INHERITED_KERNEL_VERIFIED")

    def test_offline_child_requires_explicit_profile_without_inherited_denial(self):
        command = [sys.executable, "-I", "-B", "-c", "pass"]
        with patch.object(p, "os_network_denial", return_value={"network-outbound": 0, "network-inbound": 0}):
            with patch.object(p.subprocess, "run", return_value=p.subprocess.CompletedProcess(command, 0, "", "")) as run:
                p.offline_run(command, self.folder / "explicit-policy.json")
                self.assertEqual(run.call_args.args[0], ["/usr/bin/sandbox-exec", "-p", p.SANDBOX, *command])
                self.assertEqual(run.call_args.kwargs["env"], p.clean_env())

    def test_unavailable_kernel_policy_rejects_before_child(self):
        import ctypes
        with patch.object(ctypes, "CDLL") as library:
            library.return_value.sandbox_check.return_value = -1
            with patch.object(p.subprocess, "run") as run:
                self.reject(lambda: p.offline_run(["unexecuted"], self.folder / "failed-policy.json"))
                run.assert_not_called()


def main():
    p.guard()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    old = unittest.defaultTestLoader.loadTestsFromTestCase(existing.Integrity)
    new = unittest.defaultTestLoader.loadTestsFromTestCase(Continuation)
    names = [t.id() for t in old] + [t.id() for t in new]
    old_count, new_count = old.countTestCases(), new.countTestCases()
    suite = unittest.TestSuite([old, new])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    p.write_new(args.receipt, p.canonical({"status": "PASS" if result.wasSuccessful() else "FAIL",
        "tests": result.testsRun, "existing_tests": old_count, "new_tests": new_count,
        "failures": [(t.id(), trace) for t, trace in result.failures], "errors": [(t.id(), trace) for t, trace in result.errors],
        "cases": names, "tools": c.tools(), "os_network": "DENY_ALL", "real_http_requests": 0, "native_sdk_imports": 0}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
