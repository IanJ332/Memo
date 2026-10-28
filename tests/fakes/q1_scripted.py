"""Explicit synthetic SDK transport for Q1 controller tests; never native evidence."""
from copy import deepcopy


class ScriptedTransport:
    """Two-record scripted SDK responses, persisted across three logical processes.

    No Mem0 module, model, Docker process, socket or provider adapter is created.
    Fault callbacks run after the scripted SDK effect and may replace a response
    or raise to model an ambiguous response after a real dispatch attempt.
    """

    def __init__(self, *, faults=None, reuse_process=False, fail_start=None,
                 cleanup_result=None, before_call=None):
        self.faults = faults or {}
        self.reuse_process = reuse_process
        self.fail_start = fail_start
        self.cleanup_result = cleanup_result or {"container_absent": True, "store_absent": True}
        self.before_call = before_call
        self.records = {}
        self.histories = {}
        self.attempts = []
        self.phases = []
        self.closes = 0
        self.cleanups = 0
        self.next_id = 0

    def start_phase(self, phase):
        self.phases.append(phase)
        if self.fail_start == phase:
            raise RuntimeError("SCRIPTED_PROCESS_START_FAILURE")
        return dict(phase=phase, process_id="SIMULATED-PROCESS" if self.reuse_process else f"SIMULATED-PROCESS-{phase}",
                    provider="mem0", provider_version="2.2.1", constructions=1)

    def close_phase(self):
        self.closes += 1
        return {"closed": True}

    def cleanup(self):
        self.cleanups += 1
        return deepcopy(self.cleanup_result)

    def call(self, ordinal, request):
        self.attempts.append((ordinal, deepcopy(request)))
        if self.before_call:
            self.before_call(ordinal, request, self)
        method, args, kwargs = request["method"], request["args"], request["kwargs"]
        if method == "get_all":
            namespace = kwargs.get("user_id", kwargs.get("filters", {}).get("user_id"))
            value = {"results": [deepcopy(r) for r in self.records.values() if r["user_id"] == namespace]}
        elif method == "add":
            assert kwargs["infer"] is False
            self.next_id += 1
            native_id = f"SCRIPTED-NATIVE-{self.next_id}"
            content = args[0] if args else kwargs.get("messages")
            metadata = deepcopy(kwargs.get("metadata", {}))
            self.records[native_id] = dict(id=native_id, memory=content, user_id=kwargs["user_id"], metadata=metadata)
            self.histories[native_id] = [dict(event="ADD", memory_id=native_id, old_memory=None, new_memory=content)]
            value = {"results": [dict(id=native_id, event="ADD", memory=content)]}
        elif method == "get":
            native_id = args[0] if args else kwargs.get("memory_id")
            value = deepcopy(self.records.get(native_id))
        elif method == "search":
            namespace = kwargs.get("user_id", kwargs.get("filters", {}).get("user_id"))
            value = {"results": [dict(deepcopy(r), score=0.75) for r in self.records.values() if r["user_id"] == namespace]}
        elif method == "update":
            native_id = args[0] if args else kwargs["memory_id"]
            record = self.records[native_id]
            before = record["memory"]
            record["memory"] = kwargs["text"]
            if "metadata" in kwargs:
                record["metadata"] = deepcopy(kwargs["metadata"])
            self.histories[native_id].append(dict(event="UPDATE", memory_id=native_id,
                                                  old_memory=before, new_memory=record["memory"]))
            value = {"message": "Memory updated successfully!"}
        elif method == "delete":
            native_id = args[0] if args else kwargs["memory_id"]
            old = self.records.pop(native_id)
            self.histories[native_id].append(dict(event="DELETE", memory_id=native_id,
                                                  old_memory=old["memory"], new_memory=None))
            value = {"message": "Memory deleted successfully!"}
        elif method == "history":
            native_id = args[0] if args else kwargs["memory_id"]
            value = deepcopy(self.histories.get(native_id, []))
        else:
            raise AssertionError("UNREGISTERED_SCRIPTED_METHOD:" + str(method))
        response = dict(ordinal=ordinal, method=method, status="RETURN", value=value)
        if ordinal in self.faults:
            return self.faults[ordinal](response, self)
        return response
