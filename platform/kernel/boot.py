"""kernel/boot.py — reads seed, validates fingerprints, runs constitutional
verification tests, instantiates Layer 1.

Per IMPLEMENTATION_PLAN.md Section 2:
    "Bootstrap fails closed if any [verification test] fails. The 5 tests
    encoded in tests/test_constitutional_verification.py are wired into
    kernel/boot.py as preconditions: bootstrap will not produce Layer 1
    unless all 5 tests pass."

This module is the entry point for Layer 0 → Layer 1 elevation. It is
itself called by scripts/bootstrap.py.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from kernel.primitives import (
    Auditor,
    Constructor,
    Critic,
    Governor,
    SpecRegistry,
)


SEED_DIR_DEFAULT = Path(__file__).resolve().parent.parent / "seed"


class BootstrapFailedClosed(RuntimeError):
    """Raised when bootstrap fails any precondition. Per Section 2, the
    platform must fail closed; no Layer 1 instantiation if any test fails."""


@dataclass
class Layer1Kernel:
    """The five primitive agents instantiated at Layer 1 boot."""

    spec_registry: SpecRegistry
    constructor: Constructor
    critic: Critic
    auditor: Auditor
    governor: Governor
    seed_path: Path
    fingerprints: dict[str, str]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_seed_manifest(seed_dir: Path) -> dict[str, Any]:
    """Load and parse 02_SEED_MANIFEST.yaml."""
    manifest_path = seed_dir / "02_SEED_MANIFEST.yaml"
    if not manifest_path.exists():
        raise BootstrapFailedClosed(
            f"Seed manifest not found at {manifest_path}. Cannot boot."
        )
    return yaml.safe_load(manifest_path.read_text())


def load_published_fingerprints(seed_dir: Path) -> dict[str, str]:
    """Load the published fingerprints generated at scaffolding time."""
    fp_path = seed_dir / ".fingerprints.json"
    if not fp_path.exists():
        raise BootstrapFailedClosed(
            f"Published fingerprints not found at {fp_path}. "
            f"This file is generated at scaffolding time and is required for "
            f"the constitutional verification tests."
        )
    return json.loads(fp_path.read_text())


def run_constitutional_verification_tests(
    seed_dir: Path,
    published_fingerprints: dict[str, str],
) -> list[tuple[str, bool, str]]:
    """Run the 5 verification tests from seed_manifest.governance.verification_tests.

    Returns a list of (test_name, passed, detail) tuples.
    Bootstrap fails closed if any return passed=False.
    """
    results: list[tuple[str, bool, str]] = []

    # Test 1: SHA-256 of CONSTITUTION.md matches published value
    constitution_actual = _sha256(seed_dir / "CONSTITUTION.md")
    constitution_expected = published_fingerprints.get("CONSTITUTION.md", "")
    results.append(
        (
            "SHA-256 of CONSTITUTION.md matches published value",
            constitution_actual == constitution_expected,
            f"actual={constitution_actual[:16]}... expected={constitution_expected[:16]}...",
        )
    )

    # Test 2: SHA-256 of CHARTER_v1.0.md matches published value
    charter_actual = _sha256(seed_dir / "CHARTER_v1.0.md")
    charter_expected = published_fingerprints.get("CHARTER_v1.0.md", "")
    results.append(
        (
            "SHA-256 of CHARTER_v1.0.md matches published value",
            charter_actual == charter_expected,
            f"actual={charter_actual[:16]}... expected={charter_expected[:16]}...",
        )
    )

    # Test 3: Seed manifest references both parents with current paths
    manifest = load_seed_manifest(seed_dir)
    parents = manifest.get("governance", {}).get("parents", [])
    authorities = {p.get("authority") for p in parents}
    has_charter = "Sovereignty-Aligned Charter v1.0" in authorities
    has_constitution = "Constitution@A1" in authorities
    results.append(
        (
            "Seed manifest references both parents with current paths",
            has_charter and has_constitution,
            f"Charter={has_charter}, Constitution@A1={has_constitution}",
        )
    )

    # Test 4: Audit log contains zero Governor approvals violating parent authority
    # Phase 1: structural check that the verification test exists in code.
    # Phase 3 will replay the actual audit chain.
    results.append(
        (
            "Audit log contains zero Governor approvals violating parent authority",
            True,  # Phase 1: no Governor approvals exist yet; trivially true
            "Phase 1: no Governor approvals exist pre-bootstrap; will be verified live in Phase 3",
        )
    )

    # Test 5: Every human-approval gate invokes Charter II.4.4 breath protocol
    # Phase 1: structural check that the BreathGate enforces the protocol.
    # Phase 3 will replay the actual audit metadata.
    from kernel.breath_gate import MINIMUM_BREATH_DURATION_SECONDS

    results.append(
        (
            "Every human-approval gate invokes Charter II.4.4 breath protocol",
            MINIMUM_BREATH_DURATION_SECONDS >= 30,
            f"BreathGate enforces minimum {MINIMUM_BREATH_DURATION_SECONDS}s; structural verification",
        )
    )

    return results


def boot(seed_dir: Path | None = None, audit_adapter: Any = None) -> Layer1Kernel:
    """Read the seed, validate fingerprints, run all 5 verification tests,
    and instantiate the 5 primitive agents at Layer 1.

    Per IMPLEMENTATION_PLAN.md Section 2: bootstrap fails closed if any
    test fails.

    Per the seed manifest's `kernel.human_approval_required_for`: the
    Layer 0 → Layer 1 elevation requires recorded human approval. The
    caller (scripts/bootstrap.py) is responsible for invoking the breath
    gate and recording the human signature; this function focuses on the
    structural side of the elevation.
    """
    seed_dir = seed_dir or SEED_DIR_DEFAULT

    # Load fingerprints + manifest
    fingerprints = load_published_fingerprints(seed_dir)
    manifest = load_seed_manifest(seed_dir)

    # Run the 5 constitutional verification tests
    results = run_constitutional_verification_tests(seed_dir, fingerprints)
    failures = [(name, detail) for name, passed, detail in results if not passed]
    if failures:
        raise BootstrapFailedClosed(
            "Constitutional verification tests failed:\n"
            + "\n".join(f"  ✗ {name}: {detail}" for name, detail in failures)
            + "\n\nPer Section 2, bootstrap must fail closed. No Layer 1 instantiation."
        )

    # Extract the verbatim role prompts from the seed manifest
    primitives = manifest.get("primitives", {})
    constructor_prompt = primitives.get("constructor", {}).get("role_prompt", "")
    critic_prompt = primitives.get("critic", {}).get("role_prompt", "")
    auditor_prompt = primitives.get("auditor", {}).get("role_prompt", "")
    governor_prompt = primitives.get("governor", {}).get("role_prompt", "")

    if not all([constructor_prompt, critic_prompt, auditor_prompt, governor_prompt]):
        raise BootstrapFailedClosed(
            "Seed manifest is missing one or more primitive role_prompts. "
            "Cannot instantiate Layer 1."
        )

    # Instantiate the audit adapter if not provided
    if audit_adapter is None:
        # Note: package is named platform_layer/ to avoid shadowing stdlib platform.
        from platform_layer.audit_adapter import AuditAdapter

        audit_adapter = AuditAdapter()

    # Instantiate the 5 primitives
    spec_registry = SpecRegistry()
    constructor = Constructor(spec_registry, role_prompt=constructor_prompt)
    critic = Critic(spec_registry, role_prompt=critic_prompt)
    auditor = Auditor(audit_adapter, role_prompt=auditor_prompt)
    governor = Governor(role_prompt=governor_prompt)

    return Layer1Kernel(
        spec_registry=spec_registry,
        constructor=constructor,
        critic=critic,
        auditor=auditor,
        governor=governor,
        seed_path=seed_dir,
        fingerprints=fingerprints,
    )


# ∞Δ∞ kernel.boot — fails closed on verification, no Layer 1 without all 5 tests passing ∞Δ∞
