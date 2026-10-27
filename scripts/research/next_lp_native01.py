#!/usr/bin/env python3
"""Read-only retrospective V2 projection of the sealed R1 native SDK journals.

No native adapter is constructed. Host custody of the original inventory is an
external prerequisite; hashes check continuity, not authorship or authentication.
Only aggregate output is emitted. Original observations are never rewritten.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

if not sys.flags.isolated or not sys.dont_write_bytecode:
    raise SystemExit("Use repository .venv python -I -B")


def deny(event, args):
    if event.startswith(("socket.", "subprocess.", "os.exec", "os.spawn")) or event == "os.system":
        raise RuntimeError("OFFLINE_REANALYSIS_ONLY")


sys.addaudithook(deny)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from memlife.adapters.mem0 import Mem0MemoryAdapter
from memlife.adapters.reference import ReferenceMemoryAdapter
from memlife.models.authority import AuthorityLedger, AuthorityLedgerEntry, content_sha256
from memlife.models.lifecycle import LifecycleState
from memlife.r1.protocol import canonical, registration, strict
from memlife.r1.collection import host_fixture
from memlife.runner.authority_correlation_v2 import VERSION, HostAssociationSnapshot, storage_payload_v2

INVENTORY_SHA = "2f5c7d44d3c8b1a0e3a12a61e048a65efe7438c9e8b3977346e7b90222daba83"
ADAPTER_SHA = "cf244d7896a1787b0bac7fb2cc0f4fa59b5ba7070411bf1f8b458ba6f0a84d16"
V2_SHA = "e0c400040a16c4018cf7eb8bc13df4bc153d8a9e5cf7327d8efda8db6d752362"


def need(condition, message):
    if not condition:
        raise ValueError(message)


class PureMem0Hooks(ReferenceMemoryAdapter):
    """Synthetic receiver for unchanged pure Mem0 hooks, never a native instance."""
    @property
    def trace_provenance_status(self):
        return Mem0MemoryAdapter.trace_provenance_status.fget(self)

    @property
    def trace_source_surface(self):
        return Mem0MemoryAdapter.trace_source_surface.fget(self)


class RetainedEvidence:
    def __init__(self, root):
        self.root = Path(root).resolve()
        raw = (self.root / "inventory.json").read_bytes()
        need(hashlib.sha256(raw).hexdigest() == INVENTORY_SHA, "ORIGINAL_INVENTORY_DRIFT")
        self.rows = {}
        for row in strict(raw)["files"]:
            name = row["path"]
            need(name not in self.rows, "DUPLICATE_INVENTORY_PATH")
            path = self.root / name
            need(not Path(name).is_absolute() and path.resolve().is_relative_to(self.root)
                 and not path.is_symlink(), "EVIDENCE_PATH_ESCAPE")
            data = path.read_bytes()
            need(len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
                 "ORIGINAL_MEMBER_DRIFT")
            self.rows[name] = row

    def read(self, name):
        need(name in self.rows, "UNINDEXED_EVIDENCE")
        data = (self.root / name).read_bytes()
        row = self.rows[name]
        need(len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
             "EVIDENCE_CHANGED_DURING_ANALYSIS")
        return strict(data)


def analyze(root):
    evidence = RetainedEvidence(root)
    need(hashlib.sha256((ROOT / "src/memlife/adapters/mem0.py").read_bytes()).hexdigest() == ADAPTER_SHA,
         "ORIGINAL_MEM0_ADAPTER_DRIFT")
    need(hashlib.sha256((ROOT / "src/memlife/runner/authority_correlation_v2.py").read_bytes()).hexdigest() == V2_SHA,
         "ACCEPTED_V2_SOURCE_DRIFT")
    design, acl, *_ = registration()
    blocks = {b["block_id"]: b for b in design["blocks"]}
    host_acls = {a["block_id"]: a for a in acl["records"]}
    totals, classes, metadata_keys, binding_digests = Counter(), Counter(), set(), []
    adapter = PureMem0Hooks()
    for block_id, block in blocks.items():
        for condition in ("CONTROL", "CONFLICT"):
            prefix = f"native/{block_id}__{condition}"
            job = evidence.read(prefix + "/job.json")
            memories = ([block["current_record"]] if condition == "CONTROL" else
                        [block[name] for name in block["write_order_conflict"]])
            need(job["memories"] == memories and job["provider"] == "mem0"
                 and job["provider_version"] == "2.2.1"
                 and job["source_files_sha256"]["src/memlife/adapters/mem0.py"] == ADAPTER_SHA,
                 "HOST_JOB_DESIGN_MISMATCH")
            expected_acl = host_fixture(block, host_acls[block_id])
            need(job["host_acl"] == expected_acl, "REGISTERED_HOST_AUTHORITY_SNAPSHOT")
            phase_results = [evidence.read(prefix + f"/{p}/result.json") for p in ("exercise", "reopen")]
            first, reopened = phase_results
            need(first["owned_ids"] == reopened["owned_ids"]
                 and first["container_id"] != reopened["container_id"], "REOPEN_IDENTITY")
            namespace = first["native_namespace"]
            need(namespace == reopened["native_namespace"], "REOPEN_SCOPE")
            associations, entries, expected = [], [], {}
            add_inputs = sorted(n for n in evidence.rows if n.startswith(prefix + "/exercise/capture/native-sdk/")
                                and n.endswith("-input.json") and evidence.read(n)["method"] == "add")
            need(len(add_inputs) == len(memories), "ADD_COUNT")
            for index, name in enumerate(add_inputs):
                request = evidence.read(name)
                result = evidence.read(name.replace("-input.json", "-return.json"))
                need(request["args"] == [memories[index]] and request["kwargs"]["infer"] is False
                     and request["kwargs"]["user_id"] == namespace, "HOST_INPUT_BINDING")
                need(len(result["results"]) == 1, "AMBIGUOUS_ADD")
                native = result["results"][0]
                native_id = native["id"]
                need(native["memory"] == memories[index] and native_id == first["owned_ids"][str(index)]
                     and native_id not in expected, "HOST_ADD_RESPONSE_BINDING")
                expected[native_id] = memories[index]
                event_id = f"RETROSPECTIVE:{block_id}:{condition}:WRITE:{index}"
                digest = content_sha256(memories[index])
                current = memories[index] == block["current_record"]
                entries.append(AuthorityLedgerEntry(experiment_event_id=event_id, logical_fact_id=event_id,
                    namespace=namespace, sequence=index + 1, lifecycle_state=LifecycleState.ACTIVE,
                    authoritative=current, authority_reason="REGISTERED_CURRENT_RECORD_IDENTITY_NOT_PROVIDER_METADATA",
                    source_content_sha256=digest))
                associations.append(dict(provider="mem0-oss-2.2.1", namespace=namespace, record_id=native_id,
                    record_sha256=digest, source_native_id=native_id, event_id=event_id))
                totals["host_add_bindings"] += 1
            body = canonical(dict(schema_version=VERSION, associations=associations))
            binding_digests.append(hashlib.sha256(body).hexdigest())
            snapshot = HostAssociationSnapshot.from_host_bytes(body, expected_sha256=hashlib.sha256(body).hexdigest(),
                artifact_id=f"RETROSPECTIVE_HOST_RECONSTRUCTION:{block_id}:{condition}")
            ledger = AuthorityLedger(entries=tuple(entries))
            for phase, result in zip(("exercise", "reopen"), phase_results):
                need(result["job_sha256"] == hashlib.sha256(canonical(job)).hexdigest()
                     and result["host_acl"] == expected_acl
                     and result["internal_LLM_calls"] == result["internal_LLM_attempts"] == 0
                     and result["downstream_Qwen_POSTs"] == 0, "CAPTURE_JOB_OR_USAGE")
                need({r["memory_id"]: r["content"] for r in result["final_records"]} == expected,
                     "FINAL_RECORD_ID_BYTES")
                base = prefix + f"/{phase}/capture/"
                searches = [n for n in evidence.rows if n.startswith(base + "native-sdk/")
                            and n.endswith("-input.json") and evidence.read(n)["method"] == "search"]
                need(len(searches) == 1, "EXACT_ONE_RETRIEVAL")
                search = evidence.read(searches[0])
                need(search["kwargs"]["filters"]["user_id"] == namespace, "SEARCH_SCOPE")
                raw = evidence.read(searches[0].replace("-input.json", "-return.json"))
                need(raw == result["raw_retrieval"], "RAW_RETRIEVAL_COPY_DRIFT")
                records = tuple(Mem0MemoryAdapter._normalized_record(r) for r in raw["results"])
                need(len(records) == len(expected) and {r.memory_id: r.content for r in records} == expected,
                     "NATIVE_RETRIEVAL_ID_BYTES")
                for record in records:
                    metadata_keys.update(record.metadata)
                _, score = storage_payload_v2(adapter=adapter, records=records, provider="mem0-oss-2.2.1",
                    snapshot=snapshot, phase=phase, run_id="RETROSPECTIVE", ledger=ledger, provider_events={})
                need(all(o.complete for o in score.observations), "DIRECT_BINDING_INCOMPLETE")
                want = "AUTHORITATIVE_ONLY" if condition == "CONTROL" else "AUTHORITATIVE_AND_NONAUTHORITATIVE"
                need(score.exposure.value == want, "V2_REGISTERED_CURRENT_EXPOSURE")
                classes[score.exposure.value] += 1
                totals["retrieved_records"] += len(records)
                totals["complete_direct_correlations"] += len(records)
                totals["current_records_with_complete_authority_correlation"] += sum(
                    any(ledger.by_event_id()[event].authoritative for event in observation.event_ids)
                    for observation in score.observations)
                totals["retrieval_observations"] += 1
            totals["reopened_stores"] += 1
    return dict(study="NEXT-LP-NATIVE-01", basis="RETROSPECTIVE_HOST_RECONSTRUCTION_NOT_PREEXISTING_V2_CUSTODY",
        original_inventory_sha256=INVENTORY_SHA, verified_original_members=len(evidence.rows), counts=dict(totals),
        mem0_adapter_sha256=ADAPTER_SHA, v2_correction_sha256=V2_SHA,
        exposure_counts=dict(classes), observed_metadata_keys=sorted(metadata_keys),
        reconstructed_association_set_sha256=hashlib.sha256(canonical(binding_digests)).hexdigest(),
        host_authority_design_sha256=hashlib.sha256((ROOT / "manifests/r1-memory-necessity-v1.json").read_bytes()).hexdigest(),
        host_authority_acl_sha256=hashlib.sha256((ROOT / "manifests/r1-memory-necessity-host-acl-v1.json").read_bytes()).hexdigest(),
        new_native_operations=0, new_hosted_model_requests=0, jetstream_actions=0,
        exact_metadata_substitution_treatment="NOT_OBSERVED", deployed_callers="NOT_MIGRATED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args.evidence_root), sort_keys=True, indent=2))
