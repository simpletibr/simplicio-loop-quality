#!/usr/bin/env python3
"""Deterministic flow generator and drift checker for simplicio-loop-quality.

Implements contract `simplicio.flow/v1` (simplicio-mapper#657 / simplicio-loop-quality#165):
- Reads/maintains `docs/flow/simplicio-loop-quality.flow.json` (source of truth).
- Validates drift: every referenced source file and symbol line must exist.
- Compiles `docs/flow/simplicio-loop-quality.mmd` (Mermaid flowchart).
- Renders `docs/flow/simplicio-loop-quality.svg` and `docs/flow/simplicio-loop-quality.png` via mmdc.
- Emits `docs/flow/langflow/simplicio-loop-quality.langflow.json` (importable in Langflow 1.12).
- Emits helper components for Langflow custom nodes.
- Optionally pushes to Langflow (`--push-langflow http://localhost:7860`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

FLOW_SCHEMA = "simplicio.flow/v1"
REPO_ROOT = Path(__file__).resolve().parent.parent
FLOW_DIR = REPO_ROOT / "docs" / "flow"
FLOW_JSON_PATH = FLOW_DIR / "simplicio-loop-quality.flow.json"
MMD_PATH = FLOW_DIR / "simplicio-loop-quality.mmd"
SVG_PATH = FLOW_DIR / "simplicio-loop-quality.svg"
PNG_PATH = FLOW_DIR / "simplicio-loop-quality.png"
LANGFLOW_DIR = FLOW_DIR / "langflow"
LANGFLOW_JSON_PATH = LANGFLOW_DIR / "simplicio-loop-quality.langflow.json"
COMPONENTS_DIR = LANGFLOW_DIR / "components"


def get_default_flow_data() -> dict[str, Any]:
    return {
        "$schema": FLOW_SCHEMA,
        "schema": FLOW_SCHEMA,
        "name": "simplicio-loop-quality",
        "version": "0.1.1",
        "description": "Fluxo declarativo end-to-end do simplicio-loop-quality: entrada -> passos -> saídas",
        "inputs": [
            {
                "id": "in_cli",
                "label": "CLI: simplicio-loop-quality (doctor, plan, run, gate, agents)",
                "kind": "input",
                "source": {
                    "file": "src/simplicio_loop_quality/cli.py",
                    "line": 335,
                    "symbol": "def main"
                }
            },
            {
                "id": "in_provider",
                "label": "Loop Extension Entrypoint: native provider runtime",
                "kind": "input",
                "source": {
                    "file": "src/simplicio_loop_quality/provider.py",
                    "line": 68,
                    "symbol": "def provider"
                }
            },
            {
                "id": "in_policy",
                "label": "Quality Policy: Strict Default & Lane Thresholds",
                "kind": "input",
                "source": {
                    "file": "src/simplicio_loop_quality/policy.py",
                    "line": 360,
                    "symbol": "def load_policy"
                }
            },
            {
                "id": "in_repo_sources",
                "label": "Repository Sources: Target workspace and test files",
                "kind": "input",
                "source": {
                    "file": "src/simplicio_loop_quality/quality_planner.py",
                    "line": 31,
                    "symbol": "def compile_quality_plan"
                }
            },
            {
                "id": "in_evidence_receipts",
                "label": "Execution Receipts: Raw test runner and agent evidence",
                "kind": "input",
                "source": {
                    "file": "src/simplicio_loop_quality/evidence.py",
                    "line": 350,
                    "symbol": "class EvidenceStore"
                }
            }
        ],
        "nodes": [
            {
                "id": "step_negotiation",
                "label": "Extension Handshake & Atomic Loop Capability Negotiation",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/loop_negotiation.py",
                    "line": 41,
                    "symbol": "def negotiate_loop"
                }
            },
            {
                "id": "step_quality_planner",
                "label": "36-Lane Quality Plan Compiler & Applicability Matrix",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/quality_planner.py",
                    "line": 31,
                    "symbol": "def compile_quality_plan"
                }
            },
            {
                "id": "step_risk_selection",
                "label": "Impact Analysis & Risk-Based Monotonic Lane Selection",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/risk_selection.py",
                    "line": 101,
                    "symbol": "def assess_risk"
                }
            },
            {
                "id": "step_stage_graph",
                "label": "Fan-In Deterministic Quality Stage Graph Compilation",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/stage_graph.py",
                    "line": 29,
                    "symbol": "def compile_stage_graph"
                }
            },
            {
                "id": "step_unit_testing",
                "label": "Unit & Component Quality Lane Planning and Normalization",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/unit_quality.py",
                    "line": 85,
                    "symbol": "def plan_unit_tests"
                }
            },
            {
                "id": "step_static_quality",
                "label": "Static Quality & Multi-Linter Tool Analysis",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/static_quality.py",
                    "line": 90,
                    "symbol": "def plan_static_quality"
                }
            },
            {
                "id": "step_supply_chain",
                "label": "Supply Chain, Lockfile Digests & SBOM Validation",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/supply_chain.py",
                    "line": 16,
                    "symbol": "def plan_supply_chain"
                }
            },
            {
                "id": "step_property_fuzz",
                "label": "Property-Based & Seeded Fuzzing Quality Lane",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/property_fuzz.py",
                    "line": 28,
                    "symbol": "def plan_fuzz"
                }
            },
            {
                "id": "step_mutation_testing",
                "label": "Mutation Testing & Kill Operator Verification",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/mutation_quality.py",
                    "line": 51,
                    "symbol": "def plan_mutation"
                }
            },
            {
                "id": "step_system_e2e",
                "label": "System & User-Visible End-to-End Scenarios",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/system_e2e.py",
                    "line": 26,
                    "symbol": "def plan_system_e2e"
                }
            },
            {
                "id": "step_concurrency_perf",
                "label": "Concurrency Reliability & Performance Latency Gates",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/concurrency_reliability.py",
                    "line": 26,
                    "symbol": "def plan_concurrency"
                }
            },
            {
                "id": "step_fast_conformance",
                "label": "Fast Python/Rust Conformance & Shadow Drift Verifier",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/fast_conformance.py",
                    "line": 40,
                    "symbol": "def evaluate_conformance"
                }
            },
            {
                "id": "step_evidence_audit",
                "label": "Independent Evidence Auditor (Admissibility & Freshness)",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/evidence_audit.py",
                    "line": 52,
                    "symbol": "def audit_evidence"
                }
            },
            {
                "id": "step_asolaria_quorum",
                "label": "ASOLARIA Tri-Vantage Quorum Ledger Evaluator",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/asolaria_quorum.py",
                    "line": 12,
                    "symbol": "def evaluate_quorum"
                }
            },
            {
                "id": "step_waivers_evaluation",
                "label": "Independent Scoped Waiver Selector & Expired Checks",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/waivers.py",
                    "line": 58,
                    "symbol": "def evaluate_waiver"
                }
            },
            {
                "id": "step_quality_gate",
                "label": "Fail-Closed Quality Gate Decision Oracle",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/gate.py",
                    "line": 301,
                    "symbol": "def evaluate_receipt"
                }
            },
            {
                "id": "step_remediation_findings",
                "label": "Structured Remediation Findings & Recovery Plan",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/remediation.py",
                    "line": 32,
                    "symbol": "def normalize_findings"
                }
            },
            {
                "id": "step_release_candidate",
                "label": "Reproducible Release Candidate Verification & Attestation",
                "kind": "step",
                "source": {
                    "file": "src/simplicio_loop_quality/release_candidate.py",
                    "line": 19,
                    "symbol": "def evaluate_release_candidate"
                }
            },
            {
                "id": "store_contracts",
                "label": "Canonical Contract Schemas & Strict Policies",
                "kind": "store",
                "source": {
                    "file": "src/simplicio_loop_quality/contract_validation.py",
                    "line": 21,
                    "symbol": "def validate_contract_document"
                }
            },
            {
                "id": "store_journal_events",
                "label": "Immutable Quality Event Journal & Ledger Store",
                "kind": "store",
                "source": {
                    "file": "src/simplicio_loop_quality/journal_events.py",
                    "line": 13,
                    "symbol": "def event_key"
                }
            }
        ],
        "edges": [
            {
                "from": "in_provider",
                "to": "step_negotiation",
                "label": "handshake",
                "evidence": "src/simplicio_loop_quality/loop_negotiation.py:41"
            },
            {
                "from": "store_contracts",
                "to": "step_negotiation",
                "label": "contract matrix",
                "evidence": "src/simplicio_loop_quality/contract_validation.py:21"
            },
            {
                "from": "in_cli",
                "to": "step_quality_planner",
                "label": "command request",
                "evidence": "src/simplicio_loop_quality/cli.py:335"
            },
            {
                "from": "in_policy",
                "to": "step_quality_planner",
                "label": "policy thresholds",
                "evidence": "src/simplicio_loop_quality/policy.py:360"
            },
            {
                "from": "in_repo_sources",
                "to": "step_quality_planner",
                "label": "scan workspace",
                "evidence": "src/simplicio_loop_quality/quality_planner.py:31"
            },
            {
                "from": "step_quality_planner",
                "to": "step_risk_selection",
                "label": "planned lanes",
                "evidence": "src/simplicio_loop_quality/risk_selection.py:101"
            },
            {
                "from": "step_risk_selection",
                "to": "step_stage_graph",
                "label": "selected suites",
                "evidence": "src/simplicio_loop_quality/stage_graph.py:29"
            },
            {
                "from": "step_stage_graph",
                "to": "step_unit_testing",
                "label": "unit stage",
                "evidence": "src/simplicio_loop_quality/unit_quality.py:85"
            },
            {
                "from": "step_stage_graph",
                "to": "step_static_quality",
                "label": "static stage",
                "evidence": "src/simplicio_loop_quality/static_quality.py:90"
            },
            {
                "from": "step_stage_graph",
                "to": "step_supply_chain",
                "label": "supply chain stage",
                "evidence": "src/simplicio_loop_quality/supply_chain.py:16"
            },
            {
                "from": "step_stage_graph",
                "to": "step_property_fuzz",
                "label": "fuzz stage",
                "evidence": "src/simplicio_loop_quality/property_fuzz.py:28"
            },
            {
                "from": "step_stage_graph",
                "to": "step_mutation_testing",
                "label": "mutation stage",
                "evidence": "src/simplicio_loop_quality/mutation_quality.py:51"
            },
            {
                "from": "step_stage_graph",
                "to": "step_system_e2e",
                "label": "e2e stage",
                "evidence": "src/simplicio_loop_quality/system_e2e.py:26"
            },
            {
                "from": "step_stage_graph",
                "to": "step_concurrency_perf",
                "label": "perf & reliability",
                "evidence": "src/simplicio_loop_quality/concurrency_reliability.py:26"
            },
            {
                "from": "step_stage_graph",
                "to": "step_fast_conformance",
                "label": "conformance stage",
                "evidence": "src/simplicio_loop_quality/fast_conformance.py:40"
            },
            {
                "from": "step_quality_planner",
                "to": "out_quality_plan",
                "label": "emit plan",
                "evidence": "src/simplicio_loop_quality/cli.py:208"
            },
            {
                "from": "in_evidence_receipts",
                "to": "step_evidence_audit",
                "label": "raw receipts",
                "evidence": "src/simplicio_loop_quality/evidence.py:350"
            },
            {
                "from": "step_unit_testing",
                "to": "step_evidence_audit",
                "label": "unit evidence",
                "evidence": "src/simplicio_loop_quality/evidence_audit.py:52"
            },
            {
                "from": "step_static_quality",
                "to": "step_evidence_audit",
                "label": "static findings",
                "evidence": "src/simplicio_loop_quality/evidence_audit.py:52"
            },
            {
                "from": "step_supply_chain",
                "to": "step_evidence_audit",
                "label": "sbom digests",
                "evidence": "src/simplicio_loop_quality/evidence_audit.py:52"
            },
            {
                "from": "step_property_fuzz",
                "to": "step_evidence_audit",
                "label": "fuzz results",
                "evidence": "src/simplicio_loop_quality/evidence_audit.py:52"
            },
            {
                "from": "step_mutation_testing",
                "to": "step_evidence_audit",
                "label": "mutation kills",
                "evidence": "src/simplicio_loop_quality/evidence_audit.py:52"
            },
            {
                "from": "step_system_e2e",
                "to": "step_evidence_audit",
                "label": "scenario traces",
                "evidence": "src/simplicio_loop_quality/evidence_audit.py:52"
            },
            {
                "from": "step_concurrency_perf",
                "to": "step_evidence_audit",
                "label": "metrics receipts",
                "evidence": "src/simplicio_loop_quality/evidence_audit.py:52"
            },
            {
                "from": "step_fast_conformance",
                "to": "step_evidence_audit",
                "label": "engine parity",
                "evidence": "src/simplicio_loop_quality/evidence_audit.py:52"
            },
            {
                "from": "step_evidence_audit",
                "to": "step_asolaria_quorum",
                "label": "audited evidence",
                "evidence": "src/simplicio_loop_quality/asolaria_quorum.py:12"
            },
            {
                "from": "step_asolaria_quorum",
                "to": "out_asolaria_receipt",
                "label": "3-perspective quorum",
                "evidence": "src/simplicio_loop_quality/asolaria_quorum.py:12"
            },
            {
                "from": "step_waivers_evaluation",
                "to": "step_quality_gate",
                "label": "approved waivers",
                "evidence": "src/simplicio_loop_quality/waivers.py:58"
            },
            {
                "from": "step_evidence_audit",
                "to": "step_quality_gate",
                "label": "admissible receipts",
                "evidence": "src/simplicio_loop_quality/gate.py:301"
            },
            {
                "from": "store_contracts",
                "to": "step_quality_gate",
                "label": "strict policy schema",
                "evidence": "src/simplicio_loop_quality/contract_validation.py:21"
            },
            {
                "from": "step_quality_gate",
                "to": "store_journal_events",
                "label": "append event",
                "evidence": "src/simplicio_loop_quality/journal_events.py:13"
            },
            {
                "from": "step_quality_gate",
                "to": "out_gate_verdict",
                "label": "gate verdict (PASS/BLOCKED)",
                "evidence": "src/simplicio_loop_quality/cli.py:257"
            },
            {
                "from": "step_quality_gate",
                "to": "out_evidence_manifest",
                "label": "evidence manifest",
                "evidence": "src/simplicio_loop_quality/evidence.py:350"
            },
            {
                "from": "step_quality_gate",
                "to": "step_remediation_findings",
                "label": "blocked defects",
                "evidence": "src/simplicio_loop_quality/remediation.py:32"
            },
            {
                "from": "step_remediation_findings",
                "to": "out_remediation_report",
                "label": "recovery plan",
                "evidence": "src/simplicio_loop_quality/remediation.py:32"
            },
            {
                "from": "step_quality_gate",
                "to": "step_release_candidate",
                "label": "passed candidate",
                "evidence": "src/simplicio_loop_quality/release_candidate.py:19"
            },
            {
                "from": "step_release_candidate",
                "to": "out_rc_bundle",
                "label": "attested provenance",
                "evidence": "src/simplicio_loop_quality/release_candidate.py:19"
            }
        ],
        "outputs": [
            {
                "id": "out_quality_plan",
                "label": "Quality Task Plan (quality-task.md / JSON)",
                "kind": "output",
                "source": {
                    "file": "src/simplicio_loop_quality/cli.py",
                    "line": 208,
                    "symbol": "def cmd_plan"
                }
            },
            {
                "id": "out_evidence_manifest",
                "label": "Immutable Quality Evidence Manifest & Receipts",
                "kind": "output",
                "source": {
                    "file": "src/simplicio_loop_quality/evidence.py",
                    "line": 350,
                    "symbol": "class EvidenceStore"
                }
            },
            {
                "id": "out_gate_verdict",
                "label": "Fail-Closed Quality Gate Verdict (quality-evidence.json)",
                "kind": "output",
                "source": {
                    "file": "src/simplicio_loop_quality/cli.py",
                    "line": 257,
                    "symbol": "def cmd_gate"
                }
            },
            {
                "id": "out_asolaria_receipt",
                "label": "ASOLARIA Tri-Vantage Quorum Receipt",
                "kind": "output",
                "source": {
                    "file": "src/simplicio_loop_quality/asolaria_quorum.py",
                    "line": 12,
                    "symbol": "def evaluate_quorum"
                }
            },
            {
                "id": "out_remediation_report",
                "label": "Structured Remediation Findings Report for Loop Recovery",
                "kind": "output",
                "source": {
                    "file": "src/simplicio_loop_quality/remediation.py",
                    "line": 32,
                    "symbol": "def normalize_findings"
                }
            },
            {
                "id": "out_rc_bundle",
                "label": "Signed Release Candidate Bundle & Provenance",
                "kind": "output",
                "source": {
                    "file": "src/simplicio_loop_quality/release_candidate.py",
                    "line": 19,
                    "symbol": "def evaluate_release_candidate"
                }
            }
        ],
        "generation": {
            "generator": "scripts/generate_flow.py",
            "contract": FLOW_SCHEMA,
            "deterministic": True
        }
    }


def validate_drift(data: dict[str, Any]) -> list[str]:
    """Verify that all files and commands referenced in flow.json exist."""
    errors: list[str] = []
    all_elements = data.get("inputs", []) + data.get("nodes", []) + data.get("outputs", [])

    for elem in all_elements:
        elem_id = elem.get("id", "unknown")
        src = elem.get("source", {})
        file_rel = src.get("file")
        if not file_rel:
            errors.append(f"Node {elem_id}: missing 'source.file'")
            continue
        full_path = REPO_ROOT / file_rel
        if not full_path.exists():
            errors.append(f"Drift detected in {elem_id}: file '{file_rel}' does not exist on disk")
            continue
        line_num = src.get("line")
        symbol = src.get("symbol")
        if line_num and isinstance(line_num, int) and line_num > 0:
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                if line_num > len(lines):
                    errors.append(f"Drift in {elem_id}: line {line_num} exceeds {len(lines)} lines of {file_rel}")
                elif symbol:
                    window = lines[max(0, line_num - 20):min(len(lines), line_num + 20)]
                    if not any(symbol in l for l in window):
                        errors.append(f"Drift in {elem_id}: symbol '{symbol}' not found near line {line_num} in {file_rel}")
            except Exception as e:
                errors.append(f"Could not read {file_rel}: {e}")

    for edge in data.get("edges", []):
        evidence = edge.get("evidence", "")
        if ":" in evidence:
            f_rel, _ = evidence.split(":", 1)
            if not (REPO_ROOT / f_rel).exists():
                errors.append(f"Edge {edge.get('from')}->{edge.get('to')}: evidence file '{f_rel}' not found")

    return errors


def build_mermaid(data: dict[str, Any]) -> str:
    """Build deterministic Mermaid flowchart TD representation."""
    lines: list[str] = [
        "%% Auto-generated deterministic Mermaid flow for simplicio-loop-quality (simplicio.flow/v1)",
        "flowchart TD",
        "    classDef inputStyle fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1;",
        "    classDef stepStyle fill:#f8fafc,stroke:#64748b,stroke-width:1.5px,color:#0f172a;",
        "    classDef storeStyle fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#92400e;",
        "    classDef outputStyle fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#15803d;",
        "",
        "    subgraph Inputs [\"Entradas\"]"
    ]

    for inp in sorted(data.get("inputs", []), key=lambda x: x["id"]):
        label = inp["label"].replace('"', "'")
        lines.append(f"        {inp['id']}[\"{label}\"]:::inputStyle")
    lines.append("    end")
    lines.append("")

    lines.append("    subgraph Steps [\"Processamento e Quality Gates (36 Lanes)\"]")
    step_nodes = [n for n in data.get("nodes", []) if n.get("kind") == "step"]
    for step in sorted(step_nodes, key=lambda x: x["id"]):
        label = step["label"].replace('"', "'")
        lines.append(f"        {step['id']}[\"{label}\"]:::stepStyle")
    lines.append("    end")
    lines.append("")

    store_nodes = [n for n in data.get("nodes", []) if n.get("kind") == "store"]
    if store_nodes:
        lines.append("    subgraph Stores [\"Armazenamento, Contratos e Ledger\"]")
        for store in sorted(store_nodes, key=lambda x: x["id"]):
            label = store["label"].replace('"', "'")
            lines.append(f"        {store['id']}[(\"{label}\")]:::storeStyle")
        lines.append("    end")
        lines.append("")

    lines.append("    subgraph Outputs [\"Saídas e Vereditos\"]")
    for out in sorted(data.get("outputs", []), key=lambda x: x["id"]):
        label = out["label"].replace('"', "'")
        lines.append(f"        {out['id']}[\"{label}\"]:::outputStyle")
    lines.append("    end")
    lines.append("")

    lines.append("    %% Conexões determinísticas")
    edges = sorted(data.get("edges", []), key=lambda e: (e["from"], e["to"]))
    for edge in edges:
        lbl = edge.get("label", "").replace('"', "'")
        if lbl:
            lines.append(f"    {edge['from']} -->|\"{lbl}\"| {edge['to']}")
        else:
            lines.append(f"    {edge['from']} --> {edge['to']}")

    return "\n".join(lines) + "\n"


def build_langflow_json(data: dict[str, Any]) -> dict[str, Any]:
    """Generate a Langflow 1.12.0 compatible flow definition."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    columns: dict[str, int] = {
        "input": 50,
        "step": 450,
        "store": 950,
        "output": 1350
    }
    y_offsets: dict[str, int] = {
        "input": 50,
        "step": 50,
        "store": 50,
        "output": 50
    }

    all_nodes = data.get("inputs", []) + data.get("nodes", []) + data.get("outputs", [])
    for node in sorted(all_nodes, key=lambda x: x["id"]):
        kind = node.get("kind", "step")
        x = columns.get(kind, 450)
        y = y_offsets.get(kind, 50)
        y_offsets[kind] = y + 140

        nodes.append({
            "id": node["id"],
            "type": "genericNode",
            "position": {"x": x, "y": y},
            "data": {
                "type": "CustomComponent",
                "id": node["id"],
                "node": {
                    "display_name": node["label"],
                    "description": f"Source: {node.get('source', {}).get('file', '')}:{node.get('source', {}).get('line', '')}",
                    "template": {
                        "kind": {"type": "str", "value": kind},
                        "file": {"type": "str", "value": node.get("source", {}).get("file", "")},
                        "line": {"type": "int", "value": node.get("source", {}).get("line", 0)},
                        "symbol": {"type": "str", "value": node.get("source", {}).get("symbol", "")}
                    }
                }
            }
        })

    for idx, edge in enumerate(sorted(data.get("edges", []), key=lambda e: (e["from"], e["to"]))):
        edges.append({
            "id": f"edge_{idx}_{edge['from']}_{edge['to']}",
            "source": edge["from"],
            "target": edge["to"],
            "data": {
                "label": edge.get("label", ""),
                "evidence": edge.get("evidence", "")
            }
        })

    return {
        "name": "simplicio-loop-quality",
        "description": data.get("description", "Simplicio Loop Quality Flow"),
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.8}
        }
    }


def emit_langflow_components() -> None:
    """Emit the custom python components for Langflow import."""
    COMPONENTS_DIR.mkdir(parents=True, exist_ok=True)

    flow_node_code = '''"""Simplicio Flow Node custom component for Langflow 1.12."""
from typing import Optional
try:
    from langflow.custom import Component
    from langflow.io import Output, StrInput, IntInput
    from langflow.schema import Data
except ImportError:
    class Component: pass
    Output = StrInput = IntInput = Data = object

class SimplicioFlowNode(Component):
    display_name = "Simplicio Flow Node"
    description = "Represents an Input, Step, Store, or Output node from simplicio.flow/v1"
    icon = "shield-check"

    inputs = [
        StrInput(name="node_id", display_name="Node ID", value=""),
        StrInput(name="kind", display_name="Kind (input|step|store|output)", value="step"),
        StrInput(name="source_file", display_name="Source File", value=""),
        IntInput(name="source_line", display_name="Source Line", value=0),
        StrInput(name="source_symbol", display_name="Source Symbol", value=""),
    ]

    outputs = [
        Output(display_name="Node Data", name="data", method="build_data"),
    ]

    def build_data(self) -> Data:
        return Data(value={
            "id": self.node_id,
            "kind": self.kind,
            "source": {
                "file": self.source_file,
                "line": self.source_line,
                "symbol": self.source_symbol,
            }
        })
'''
    (COMPONENTS_DIR / "simplicio_flow_node.py").write_text(flow_node_code, encoding="utf-8")

    map_reader_code = '''"""Simplicio Map Reader custom component for Langflow 1.12."""
import json
from pathlib import Path
try:
    from langflow.custom import Component
    from langflow.io import Output, StrInput
    from langflow.schema import Data
except ImportError:
    class Component: pass
    Output = StrInput = Data = object

class SimplicioMapReader(Component):
    display_name = "Simplicio Map Reader"
    description = "Reads .simplicio/ or docs/flow/ artifacts into Langflow"
    icon = "folder-search"

    inputs = [
        StrInput(name="flow_json_path", display_name="Flow JSON Path", value="docs/flow/simplicio-loop-quality.flow.json"),
    ]

    outputs = [
        Output(display_name="Flow Payload", name="payload", method="read_flow"),
    ]

    def read_flow(self) -> Data:
        path = Path(self.flow_json_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            return Data(value={"error": f"Path not found: {path}"})
        with open(path, "r", encoding="utf-8") as f:
            return Data(value=json.load(f))
'''
    (COMPONENTS_DIR / "simplicio_map_reader.py").write_text(map_reader_code, encoding="utf-8")


def render_images(mmd_file: Path, svg_file: Path, png_file: Path) -> dict[str, str]:
    """Render Mermaid diagram to SVG and PNG using mmdc, failing explicitly if blocked."""
    statuses = {"svg": "blocked(mmdc ausente)", "png": "blocked(mmdc ausente)"}

    puppeteer_cfg = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    try:
        json.dump({"args": ["--no-sandbox"]}, puppeteer_cfg)
        puppeteer_cfg.close()

        mmdc_bin = shutil.which("mmdc") or "mmdc"
        for target, out_path in [("svg", svg_file), ("png", png_file)]:
            cmd = [
                mmdc_bin,
                "-i", str(mmd_file),
                "-o", str(out_path),
                "-p", puppeteer_cfg.name
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                    statuses[target] = "ok"
                else:
                    err_msg = res.stderr.strip()[:100] or res.stdout.strip()[:100] or "unknown error"
                    statuses[target] = f"blocked({err_msg})"
            except FileNotFoundError:
                statuses[target] = "blocked(mmdc not installed)"
            except subprocess.TimeoutExpired:
                statuses[target] = "blocked(mmdc timeout)"
            except Exception as ex:
                statuses[target] = f"blocked({ex})"
    finally:
        if os.path.exists(puppeteer_cfg.name):
            os.remove(puppeteer_cfg.name)

    return statuses


def push_to_langflow(langflow_url: str, flow_payload: dict[str, Any]) -> tuple[bool, str]:
    """Push flow to a running Langflow instance and verify retrieval."""
    url = langflow_url.rstrip("/") + "/api/v1/flows/"
    data = json.dumps(flow_payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            res_json = json.loads(body)
            flow_id = res_json.get("id")
            if not flow_id:
                return False, f"Langflow POST succeeded but returned no flow ID: {body[:200]}"

            get_req = urllib.request.Request(f"{url}{flow_id}", method="GET")
            with urllib.request.urlopen(get_req, timeout=5) as get_resp:
                if 200 <= get_resp.status < 300:
                    return True, f"Imported flow ID {flow_id} verified via GET"
                return False, f"GET verification failed with status {get_resp.status}"
    except urllib.error.URLError as e:
        return False, f"Langflow unreachable at {url}: {e}"
    except Exception as e:
        return False, f"Error pushing to Langflow: {e}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate simplicio-loop-quality flow artifacts.")
    parser.add_argument("--push-langflow", help="Langflow host to push flow (e.g. http://localhost:7860)")
    parser.add_argument("--check-drift", action="store_true", help="Only validate drift and exit.")
    args = parser.parse_args()

    FLOW_DIR.mkdir(parents=True, exist_ok=True)
    LANGFLOW_DIR.mkdir(parents=True, exist_ok=True)

    if FLOW_JSON_PATH.exists():
        with open(FLOW_JSON_PATH, "r", encoding="utf-8") as f:
            flow_data = json.load(f)
    else:
        flow_data = get_default_flow_data()

    # 1. Check Drift
    drift_errors = validate_drift(flow_data)
    if drift_errors:
        print("ERROR: Drift detected in flow.json:", file=sys.stderr)
        for err in drift_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if args.check_drift:
        print("Drift check passed successfully.")
        return 0

    # 2. Save deterministic flow.json
    json_bytes = json.dumps(flow_data, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    FLOW_JSON_PATH.write_bytes(json_bytes)
    print(f"✔ Saved: {FLOW_JSON_PATH.relative_to(REPO_ROOT)}")

    # 3. Generate Mermaid .mmd
    mmd_content = build_mermaid(flow_data)
    MMD_PATH.write_text(mmd_content, encoding="utf-8")
    print(f"✔ Saved: {MMD_PATH.relative_to(REPO_ROOT)}")

    # 4. Render Images (SVG / PNG)
    img_statuses = render_images(MMD_PATH, SVG_PATH, PNG_PATH)
    print(f"  SVG status: {img_statuses['svg']}")
    print(f"  PNG status: {img_statuses['png']}")

    # 5. Generate Langflow flow JSON
    langflow_payload = build_langflow_json(flow_data)
    langflow_bytes = json.dumps(langflow_payload, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    LANGFLOW_JSON_PATH.write_bytes(langflow_bytes)
    print(f"✔ Saved: {LANGFLOW_JSON_PATH.relative_to(REPO_ROOT)}")

    # 6. Emit helper components
    emit_langflow_components()
    print(f"✔ Emitted Langflow custom components in: {COMPONENTS_DIR.relative_to(REPO_ROOT)}")

    # 7. Optional Push to Langflow
    if args.push_langflow:
        success, msg = push_to_langflow(args.push_langflow, langflow_payload)
        print(f"  Langflow Push: {'SUCCESS' if success else 'BLOCKED'} ({msg})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
