"""Offline fixture integrity checks, not an admission classifier or app test."""
import base64
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
checks = 0


def check(condition, label):
    global checks
    if not condition:
        raise ValueError(label)
    checks += 1


def load(name):
    return json.loads((ROOT / name).read_bytes())


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def decode(value):
    return base64.b64decode(value, validate=True)


def identity(value):
    return (tuple(sorted(value["scope"].items())), value["record_id"])


def current_binding(value):
    return (identity(value), value["event_id"], value["host_revision"],
            value["expected_content_sha256"])


def verify_host(snapshot, source):
    check(snapshot["snapshot_complete"] is True, "fixture snapshot completeness")
    check(snapshot["store_identity"] == "fixture-host-evidence-store-01", "Host store")
    check(type(snapshot["snapshot_generation"]) is int, "Host generation")
    for association in snapshot["associations"]:
        event = source[association["event_id"]]
        check(association["expected_content_sha256"] == event["content_sha256"],
              "Host expected digest must originate in independent source catalog")
        check(association["source_id"] == event["source_id"], "Host event/source identity")
        check(association["expected_digest_origin"] ==
              "host-source-catalog.json:" + event["event_id"], "expected digest custody")
        check(association["created_by"] == "HOST_EVIDENCE_ADMIN" and
              association["verified_by"] == "HOST_SOURCE_VERIFIER", "Host fixture writer roles")
        check(association["status"] in {"CURRENT", "REVOKED", "SUPERSEDED"}, "Host status")
        check(type(association["host_revision"]) is int and association["host_revision"] > 0,
              "Host revision")


def main():
    manifest = load("manifest.json")
    expected_names = {m["path"] for m in manifest["members"]}
    actual_names = {p.name for p in ROOT.iterdir() if p.is_file()} - {"manifest.json"}
    check(expected_names == actual_names, "exact manifest membership")
    for member in manifest["members"]:
        data = (ROOT / member["path"]).read_bytes()
        check(len(data) == member["size_bytes"], "manifest size " + member["path"])
        check(digest(data) == member["sha256"], "manifest hash " + member["path"])

    catalog = load("host-source-catalog.json")
    source = {e["event_id"]: e for e in catalog["sources"]}
    check(len(source) == len(catalog["sources"]), "unique source events")
    for event in source.values():
        check(decode(event["content_base64"]) == event["content_utf8"].encode("utf-8"),
              "source exact bytes")
        check(digest(decode(event["content_base64"])) == event["content_sha256"],
              "source body digest")

    cases = load("cases.json")
    oracle = load("oracle.json")
    executable = [c for c in cases["cases"] if c["executable"]]
    audit = [c for c in cases["cases"] if not c["executable"]]
    check(len(executable) == 9 and len(audit) == 2, "frozen coverage counts")
    check(len({c["case_id"] for c in cases["cases"]}) == 11, "unique scenario IDs")
    by_case = {c["case_id"]: c for c in oracle["cases"]}
    check(set(by_case) == {c["case_id"] for c in executable}, "executable oracle coverage")
    check(set(cases["fixed_message"]["Submessages"][0]["Content"]["arguments"]) ==
          {"project_id", "recipient"}, "historical ToolArguments field compatibility")

    for case in executable:
        notes = copy.deepcopy(case["initial_application"]["notes"])
        snapshot = copy.deepcopy(case["initial_host"])
        reservations = {}
        confirmations = set()
        verify_host(snapshot, source)
        for event in case["lifecycle_events"]:
            if event["kind"] == "HOST_REPLACE_SNAPSHOT":
                check(event["actor"] == "HOST_EVIDENCE_ADMIN", "Host lifecycle actor")
                check(event["basis_event_id"] in source, "Host lifecycle source basis")
                check(event["snapshot"]["snapshot_generation"] > snapshot["snapshot_generation"],
                      "monotone Host snapshot generation")
                previous_current = {current_binding(a) for a in snapshot["associations"]
                                    if a["status"] == "CURRENT"}
                for association in event["snapshot"]["associations"]:
                    if association["status"] == "CURRENT":
                        binding = current_binding(association)
                        check(binding in previous_current or binding in confirmations,
                              "CURRENT publication requires prior persisted-byte confirmation")
                snapshot = copy.deepcopy(event["snapshot"])
                verify_host(snapshot, source)
            elif event["kind"] == "APPLICATION_RESERVE_RECORD_ROUTE":
                check(event["actor"] == "APPLICATION_CONTEXT_POLICY", "application routing actor")
                check(event["reservation_id"] not in reservations, "unique routing reservation")
                check(event["record_id"] not in {n["record_id"] for n in notes},
                      "reserve fresh application record identity")
                check(event["requested_use"] == "operational", "fixture reserved operational use")
                reservations[event["reservation_id"]] = event
            elif event["kind"] == "NOTE_APPEND":
                check(event["actor"] == "NOTE_WRITER", "ordinary write actor")
                check(event["note"]["record_id"] not in {n["record_id"] for n in notes},
                      "append stable ID uniqueness")
                check(event["reservation_id"] in reservations, "append requires application reservation")
                reservation = reservations.pop(event["reservation_id"])
                check(identity(event["note"]) == identity(reservation), "append reserved identity")
                check(event["note"]["requested_use"] == reservation["requested_use"] and
                      event["note"]["routing_owner"] == "APPLICATION_CONTEXT_POLICY",
                      "writer cannot choose requested use")
                notes.append(copy.deepcopy(event["note"]))
            elif event["kind"] == "NOTE_REPLACE":
                check(event["actor"] == "NOTE_WRITER", "ordinary update actor")
                positions = [i for i, n in enumerate(notes) if n["record_id"] == event["record_id"]]
                check(len(positions) == 1, "unique update target")
                old = notes[positions[0]]
                new = event["note"]
                check(old["record_id"] == new["record_id"] and old["scope"] == new["scope"],
                      "update identity unchanged")
                check(old["requested_use"] == new["requested_use"] and
                      new["routing_owner"] == "APPLICATION_CONTEXT_POLICY", "no writer routing downgrade")
                check(new["record_revision"] > old["record_revision"], "note revision increases")
                notes[positions[0]] = copy.deepcopy(new)
                confirmations = {binding for binding in confirmations if binding[0] != identity(new)}
            elif event["kind"] == "HOST_CONFIRM_PERSISTED_RECORD":
                check(event["actor"] == "HOST_SOURCE_VERIFIER", "Host confirmation actor")
                matching = [n for n in notes if identity(n) == identity(event)]
                check(len(matching) == 1, "confirmation requires one persisted scoped record")
                persisted = matching[0]
                check(event["record_revision"] == persisted["record_revision"],
                      "confirm exact persisted revision")
                check(event["observed_content_base64"] == persisted["content_base64"],
                      "confirm exact persisted bytes")
                basis = source[event["event_id"]]
                check(event["expected_digest_origin"] ==
                      "host-source-catalog.json:" + basis["event_id"], "confirmation independent basis")
                check(digest(decode(event["observed_content_base64"])) == basis["content_sha256"],
                      "persisted bytes agree with independent source body")
                confirmations.add((identity(event), event["event_id"], event["host_revision"],
                                   basis["content_sha256"]))
            else:
                raise ValueError("unknown lifecycle event")
        check(notes == case["effective_notes"], "lifecycle final note state")
        check(snapshot == case["effective_host"], "lifecycle final Host state")
        check(len({n["record_id"] for n in notes}) == len(notes), "unique retrieved IDs")
        for note in notes:
            payload = decode(note["content_base64"])
            payload.decode("utf-8", errors="strict")
            check(digest(payload) == note["content_sha256"], "candidate byte-integrity digest")
            check(note["scope"] == cases["scope"], "candidate retrieval scope")
            check(note["routing_owner"] == "APPLICATION_CONTEXT_POLICY", "trusted use routing")
            check(note["requested_use"] in {"operational", "reference"}, "use routing enum")

        expected = by_case[case["case_id"]]
        check([n["record_id"] for n in notes] == expected["expected_input_ids"], "input order")
        decisions = expected["decisions"]
        check([d["record_id"] for d in decisions] == expected["expected_input_ids"], "decision order")
        lookup = {n["record_id"]: n for n in notes}
        context = []
        for decision in decisions:
            note = lookup[decision["record_id"]]
            channel = decision["delivery_channel"]
            if channel is not None:
                check(channel == note["requested_use"], "no operational-to-reference fallback")
                check(decision["classification"] ==
                      {"operational": "CURRENT", "reference": "REFERENCE"}[channel],
                      "delivery classification consistency")
                context.append({"record_id": note["record_id"], "channel": channel,
                                "content_base64": note["content_base64"]})
            else:
                check(decision["classification"] in {"UNKNOWN", "INACTIVE"}, "omission classification")
        check(context == expected["expected_adapter_input"]["context"], "frozen delivery bytes/order")
        check([n["record_id"] for n in context] == expected["expected_delivered_ids"], "delivery IDs")
        for channel, field in [("operational", "expected_operational_context"),
                               ("reference", "expected_reference_context")]:
            check([n for n in context if n["channel"] == channel] == expected[field], "channel output")
        check(expected["expected_adapter_input"]["message"] == cases["fixed_message"], "message preserved")
        data = canonical(expected["expected_adapter_input"])
        check(decode(expected["expected_adapter_input_base64"]) == data, "exact invocation bytes")
        check(digest(data) == expected["expected_adapter_input_sha256"], "exact invocation hash")

    for case in audit:
        check(case["independent_semantic_support_label"] is None, "no manufactured semantic label")
        check(case["expected_adapter_input_sha256"] is None and
              case["expected_classification"] == "AUDIT_ONLY", "audit control excluded")
    print(json.dumps({"status": "PASS", "consistency_checks": checks,
                      "executable_scenarios": len(executable), "audit_only_scenarios": len(audit),
                      "guard_executions": 0, "application_tests": 0,
                      "manifest_sha256": digest((ROOT / "manifest.json").read_bytes())}, sort_keys=True))


if __name__ == "__main__":
    main()
