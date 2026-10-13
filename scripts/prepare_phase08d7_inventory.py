"""Read dependency metadata/artifacts only; never install or initialize a provider.

The resulting preparation receipt always preserves the BLOCKED runtime gate.
The caller supplies existing site-package directories for metadata inspection;
their .pth files and provider modules are never executed.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import email
import hashlib
import json
from pathlib import Path
import platform
import sys
import tarfile
import tomllib
from urllib.parse import urlsplit
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PIN = "f8950b0c07d9e34c76493dba802bb309f0ce60fd"
METADATA_PINS = {
    "pyproject.toml": ("e656821ca96c76b84a1d1cb1c7eb592f7f3b2563", 15638),
    "uv.lock": ("cd9687ebaa9a749e506ed396fc95c6f48925072a", 999593),
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def identity(path: Path) -> dict:
    return {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def no_network(event: str, args: tuple) -> None:
    if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo"}:
        raise RuntimeError("network is forbidden during dependency inventory")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--packaging-site", type=Path, required=True)
    parser.add_argument("--site", type=Path, action="append", default=[])
    parser.add_argument("--cache", type=Path, action="append", default=[])
    parser.add_argument("--venv-config", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sdk-plan", type=Path)
    args = parser.parse_args()
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        parser.error("use this repository's .venv interpreter")
    # Only packaging is imported from an existing repository tool environment.
    # This does not alter the clean bootstrap venv or execute that site's .pth.
    if ".venv" not in args.packaging_site.parts:
        parser.error("packaging must come from an existing repository .venv")
    sys.addaudithook(no_network)
    sys.path.insert(0, str(args.packaging_site))
    from packaging.markers import Marker, default_environment
    from packaging.requirements import Requirement
    from packaging.tags import parse_tag, sys_tags
    from packaging.utils import canonicalize_name, parse_wheel_filename

    metadata = []
    for name, (expected_blob, expected_size) in METADATA_PINS.items():
        path = args.metadata / name
        data = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != expected_blob or len(data) != expected_size:
            raise ValueError(f"pinned dependency metadata mismatch: {name}")
        metadata.append({**identity(path), "git_blob_sha1": blob})
    lock = tomllib.loads((args.metadata / "uv.lock").read_text())
    project = tomllib.loads((args.metadata / "pyproject.toml").read_text())["project"]
    environment = default_environment()
    tags = set(sys_tags())
    indexed = defaultdict(list)
    for package in lock["package"]:
        indexed[package["name"]].append(package)

    def active(marker: str | None) -> bool:
        return marker is None or Marker(marker).evaluate(environment)

    def select(edge: dict) -> dict:
        options = [p for p in indexed[edge["name"]]
                   if ("version" not in edge or p["version"] == edge["version"])
                   and ("source" not in edge or p["source"] == edge["source"])
                   and (not p.get("resolution-markers")
                        or any(active(m) for m in p["resolution-markers"]))]
        if len(options) != 1:
            raise ValueError(f"ambiguous lock dependency: {edge['name']}")
        return options[0]

    def closure(name: str, extras: tuple = ()) -> dict:
        queue = deque([{"name": name, "extra": extras}])
        selected, visited = {}, set()
        while queue:
            edge = queue.popleft()
            if not active(edge.get("marker")):
                continue
            package = select(edge)
            selected[package["name"]] = package
            for extra in ("", *edge.get("extra", ())):
                key = (package["name"], package["version"], extra)
                if key in visited:
                    continue
                visited.add(key)
                queue.extend(package.get("dependencies", ()) if not extra else
                             package.get("optional-dependencies", {}).get(extra, ()))
        return selected

    sdk = closure("openai")
    required = closure("hindsight-api-slim", ("embedded-db", "local-onnx"))
    # Verify the chosen upstream resolution satisfies direct Hindsight constraints.
    for requirement in project["dependencies"] + sum(
            [project["optional-dependencies"][x] for x in ("embedded-db", "local-onnx")], []):
        req = Requirement(requirement)
        if req.marker is None or req.marker.evaluate(environment):
            version = required[canonicalize_name(req.name)]["version"]
            if not req.specifier.contains(version, prereleases=True):
                raise ValueError(f"upstream lock violates declared requirement: {req.name}")

    observed = {}
    def remember(path: Path) -> dict:
        value = identity(path)
        observed[str(path)] = value
        return value

    sites, installed = [], defaultdict(list)
    for site in args.site:
        entries = []
        for path in sorted(site.glob("*.dist-info/METADATA")):
            info = email.message_from_bytes(path.read_bytes())
            name = canonicalize_name(info["Name"])
            record = {"name": name, "version": info["Version"], **remember(path)}
            entries.append(record)
            installed[name].append(record)
        pth = [remember(path) for path in sorted(site.glob("*.pth"))]
        sites.append({"site": str(site), "exists": site.is_dir(),
                      "distribution_count": len(entries),
                      "metadata_fingerprint": hashlib.sha256(json.dumps(
                          entries, sort_keys=True).encode()).hexdigest(),
                      "required_distributions": [e for e in entries if e["name"] in required],
                      "pth_files_read_not_executed": pth})

    artifacts, cache_summary, source_artifacts, cached_metadata = [], [], [], []
    for cache in args.cache:
        files = sorted(set(cache.rglob("*.body")) | set(cache.rglob("*.whl")))
        wheel_count = sdist_count = 0
        for path in files:
            with path.open("rb") as stream:
                head = stream.read(4)
            if head.startswith(b"\x1f\x8b"):
                try:
                    with tarfile.open(path, mode="r|gz") as archive:
                        for member in archive:
                            if member.isfile() and member.name.endswith("/PKG-INFO"):
                                stream = archive.extractfile(member)
                                info = email.message_from_bytes(stream.read())
                                sdist_count += 1
                                name = canonicalize_name(info["Name"])
                                if name in required:
                                    source_artifacts.append({"name": name, "version": info["Version"],
                                                             **remember(path)})
                                break
                except tarfile.ReadError:
                    pass  # Compressed index pages are not source distributions.
                continue
            if head == b"Meta":
                info = email.message_from_bytes(path.read_bytes())
                if info["Name"] and canonicalize_name(info["Name"]) in required:
                    cached_metadata.append({"name": canonicalize_name(info["Name"]),
                                            "version": info["Version"], **remember(path)})
                continue
            if head != b"PK\x03\x04":
                continue
            with zipfile.ZipFile(path) as archive:
                members = [n for n in archive.namelist()
                           if n.count("/") == 1 and n.endswith(".dist-info/METADATA")]
                if len(members) != 1:
                    continue
                wheel_count += 1
                info = email.message_from_bytes(archive.read(members[0]))
                name = canonicalize_name(info["Name"])
                if name not in required:
                    continue
                wheel_path = members[0].removesuffix("METADATA") + "WHEEL"
                wheel = email.message_from_bytes(archive.read(wheel_path))
                artifact_tags = set().union(*(parse_tag(t) for t in wheel.get_all("Tag", [])))
                python_req = info.get("Requires-Python")
                from packaging.specifiers import SpecifierSet
                compatible = bool(tags & artifact_tags) and (
                    not python_req or SpecifierSet(python_req).contains(platform.python_version()))
                record = {"name": name, "version": info["Version"], **remember(path),
                          "tags": sorted(str(t) for t in artifact_tags),
                          "compatible_with_target": compatible,
                          "requires_python": python_req,
                          "requires_dist": info.get_all("Requires-Dist", [])}
                artifacts.append(record)
        cache_summary.append({"path": str(cache), "exists": cache.is_dir(),
                              "body_or_wheel_files_examined": len(files),
                              "source_archives_with_pkg_info": sdist_count,
                              "wheel_archives_with_metadata": wheel_count})

    plan = []
    for name, package in sorted(required.items()):
        wheels = []
        for wheel in package.get("wheels", []):
            filename = Path(urlsplit(wheel["url"]).path).name
            if parse_wheel_filename(filename)[3] & tags:
                wheels.append({"filename": filename, "url": wheel["url"],
                               "sha256": wheel["hash"].removeprefix("sha256:"),
                               "bytes": wheel["size"]})
        local = [a for a in artifacts if a["name"] == name]
        matched = [a for a in local if a["version"] == package["version"]
                   and a["compatible_with_target"]
                   and any(a["sha256"] == w["sha256"] for w in wheels)]
        for artifact in matched:
            with zipfile.ZipFile(artifact["path"]) as archive:
                if archive.testzip() is not None:
                    raise ValueError(f"corrupt wheel: {name}")
        plan.append({"name": name, "version": package["version"],
                     "source": package["source"], "sdk_closure": name in sdk,
                     "upstream_sdist_not_authorized_for_build": package.get("sdist"),
                     "readiness": "READY_LOCAL_WHEEL" if matched else "BLOCKED",
                     "reason": None if matched else (
                         "PINNED_SOURCE_OR_RELEASE_WHEEL_NOT_LOCAL" if not wheels else
                         "NO_LOCAL_COMPATIBLE_WHEEL_MATCHING_LOCK_HASH"),
                     "compatible_upstream_wheels": wheels,
                     "local_matching_wheels": matched,
                     "local_other_artifacts": [a for a in local if a not in matched],
                     "installed_versions_metadata_only": sorted(set(
                         p["version"] for p in installed[name]))})
    configs = [remember(p) for p in args.venv_config]
    # Detect modifications during this read-only audit, including reused metadata.
    unchanged = all(identity(Path(p)) == before for p, before in observed.items())
    if not unchanged:
        raise ValueError("existing dependency artifact changed during inventory")
    receipt = {
        "phase": "08D-7", "base_commit": "d29742e9a59575d63f54c50e10205208654240c1",
        "upstream_commit": PIN, "readiness": "BLOCKED",
        "evidence_class": "DEPENDENCY_PREPARATION_NOT_RUNTIME_QUALIFICATION",
        "target": environment, "metadata": metadata, "venv_configs": configs,
        "declared_hindsight_requirements": project["dependencies"],
        "declared_hindsight_extras": {x: project["optional-dependencies"][x]
                                      for x in ("embedded-db", "local-onnx")},
        "lock_selection_is_historical_runtime_reconstruction": False,
        "sites": sites, "cache_summary": cache_summary, "packages": plan,
        "local_source_artifacts_not_authorized_for_build": source_artifacts,
        "cached_distribution_metadata_not_installable": cached_metadata,
        "summary": {"required_packages": len(plan), "sdk_packages": len(sdk),
                    "ready_local_wheels": sum(p["readiness"] != "BLOCKED" for p in plan),
                    "blocked_packages": sum(p["readiness"] == "BLOCKED" for p in plan)},
        "existing_inspected_artifacts_unchanged": unchanged,
        "dependencies_downloaded_or_installed": False,
        "providers_imported_or_initialized": False, "sdk_transport_tests_executed": False,
        "runtime_gate": "BLOCKED_UNCHANGED",
        "proposed_wheelhouse": str(ROOT / ".local/phase08d7/wheelhouse"),
        "proposed_runtime": str(ROOT / ".local/phase08d7/runtime/.venv"),
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if args.sdk_plan:
        sdk_plan = {
            "phase": "08D-7", "authorization": "REQUIRED_NOT_GRANTED",
            "scope": "SDK_ONLY_NOT_HINDSIGHT_RUNTIME_READY",
            "target": environment, "upstream_lock_sha256": metadata[1]["sha256"],
            "downloads": [{"name": p["name"], "version": p["version"],
                           "artifacts": p["compatible_upstream_wheels"]}
                          for p in plan if p["sdk_closure"] and p["readiness"] == "BLOCKED"],
            "existing_local_artifacts": [{"name": p["name"], "version": p["version"],
                                          "artifacts": p["local_matching_wheels"]}
                                         for p in plan if p["sdk_closure"]
                                         and p["readiness"] != "BLOCKED"],
            "wheelhouse": receipt["proposed_wheelhouse"],
            "runtime": receipt["proposed_runtime"],
            "network": {"acquisition_https_hosts": ["pypi.org", "files.pythonhosted.org"],
                        "exact_artifact_urls_only": True, "cross_host_redirects": False,
                        "installation_and_tests": "DENY_ALL_NETWORK_INCLUDING_LOOPBACK"},
            "installation": "OFFLINE_WHEELS_ONLY_REQUIRE_HASHES_NO_DEPS_NO_INDEX",
            "installer": {"version": "24.3.1", "target_option": "--python",
                          "repository_venv": str(args.packaging_site.parents[2]),
                          "metadata": remember(args.packaging_site / "pip-24.3.1.dist-info/METADATA")},
            "source_builds": False, "provider_initialization": False,
            "model_downloads_or_calls": False, "runtime_gate": "BLOCKED_UNCHANGED",
        }
        with args.sdk_plan.open("x", encoding="utf-8") as stream:
            json.dump(sdk_plan, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps(receipt["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
