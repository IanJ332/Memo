"""Resolve only source-demonstrated import packages against existing pinned metadata."""
from __future__ import annotations

import ast
from collections import deque

ENV = {"python_full_version": "3.12.8", "python_version": "3.12", "sys_platform": "darwin",
       "os_name": "posix", "platform_machine": "x86_64", "platform_system": "Darwin",
       "implementation_name": "cpython", "implementation_version": "3.12.8",
       "platform_python_implementation": "CPython", "extra": ""}


def active(marker):
    if marker is None:
        return True
    def operand(node):
        if isinstance(node, ast.Name) and node.id in ENV:
            return ENV[node.id]
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        raise ValueError("unresolved metadata marker operand: " + marker)
    def expression(node):
        if isinstance(node, ast.BoolOp):
            values = [expression(x) for x in node.values]
            if isinstance(node.op, ast.And): return all(values)
            if isinstance(node.op, ast.Or): return any(values)
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = operand(node.left), operand(node.comparators[0])
            variable = node.left.id if isinstance(node.left, ast.Name) else node.comparators[0].id if isinstance(node.comparators[0], ast.Name) else ""
            op = node.ops[0]
            if variable in {"python_version", "python_full_version", "implementation_version"} and not isinstance(op, (ast.In, ast.NotIn)):
                def version(text):
                    parts = tuple(int(x) for x in text.split(".")); return parts + (0,) * (8 - len(parts))
                left, right = version(left), version(right)
            operations = {ast.Eq: lambda: left == right, ast.NotEq: lambda: left != right,
                          ast.Lt: lambda: left < right, ast.LtE: lambda: left <= right,
                          ast.Gt: lambda: left > right, ast.GtE: lambda: left >= right,
                          ast.In: lambda: left in right, ast.NotIn: lambda: left not in right}
            if type(op) in operations: return operations[type(op)]()
        raise ValueError("unresolved metadata marker syntax: " + marker)
    return expression(ast.parse(marker, mode="eval").body)


def distribution(module):
    if module.startswith("opentelemetry.exporter.otlp.proto.http"):
        return "opentelemetry-exporter-otlp-proto-http"
    if module.startswith("opentelemetry.exporter.prometheus"):
        return "opentelemetry-exporter-prometheus"
    if module.startswith("opentelemetry.sdk"):
        return "opentelemetry-sdk"
    if module.startswith("opentelemetry"):
        return "opentelemetry-api"
    root = module.split(".")[0]
    mapping = {"aiohttp": "aiohttp", "asyncpg": "asyncpg", "dateparser": "dateparser",
               "dotenv": "python-dotenv", "google": "google-genai", "httpx": "httpx",
               "json_repair": "json-repair", "numpy": "numpy", "openai": "openai",
               "orjson": "orjson", "pgvector": "pgvector", "pydantic": "pydantic",
               "pydantic_core": "pydantic-core", "sqlalchemy": "sqlalchemy", "toktok": "toktok-rs", "yarl": "yarl"}
    if root not in mapping:
        raise ValueError("unmapped demonstrated external import: " + module)
    return mapping[root]


def closure(external_imports, lock, inventory):
    selected_versions = {r["name"]: r["version"] for r in inventory["packages"]}
    roots = {distribution(m) for m in external_imports}
    queue = deque((name, ()) for name in sorted(roots))
    visited, packages, edges = set(), {}, []
    while queue:
        name, extras = queue.popleft()
        candidates = [p for p in lock["package"] if p["name"] == name and p["version"] == selected_versions[name]]
        if len(candidates) != 1: raise ValueError("ambiguous target lock package: " + name)
        package = candidates[0]; packages[name] = package
        for extra in ("", *extras):
            if (name, extra) in visited: continue
            visited.add((name, extra))
            dependencies = package.get("dependencies", []) if not extra else package.get("optional-dependencies", {}).get(extra, [])
            for edge in dependencies:
                if not active(edge.get("marker")): continue
                if edge.get("version") and edge["version"] != selected_versions[edge["name"]]:
                    raise ValueError("target dependency version mismatch")
                edges.append({"from": name, "to": edge["name"], "selected_extra": extra,
                              "dependency_extras": edge.get("extra", []), "marker": edge.get("marker")})
                queue.append((edge["name"], tuple(edge.get("extra", []))))
    return {"roots": sorted(roots), "package_versions": {n: packages[n]["version"] for n in sorted(packages)},
            "edges": edges, "target": ENV, "hindsight_distribution_metadata_not_installed": True}
