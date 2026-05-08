"""scripts/bootstrap.py — reader-facing entry point.

Per IMPLEMENTATION_PLAN.md repository structure, this is the script a
reader runs to instantiate the platform locally:

    # Phase 1 only (Layer 1 / kernel):
    python -m scripts.bootstrap --seed seed/02_SEED_MANIFEST.yaml

    # Full stack through Layer 3 (Phase 5 — kernel + platform + roles):
    python -m scripts.bootstrap --full

Default mode boots through Layer 1 (kernel) only — preserves the
original Phase 1 contract. ``--full`` extends to Layer 2 (platform) and
Layer 3 (3 fully-implemented roles via the runtime factory).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kernel.boot import (
    boot,
    BootstrapFailedClosed,
    load_published_fingerprints,
    run_constitutional_verification_tests,
)
from kernel.breath_gate import BreathGate, BreathGateRefused, BreathGateTimeout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap the Breathline Agentic Platform (Phase 1: Layer 1 / kernel only)"
    )
    parser.add_argument(
        "--seed",
        type=str,
        default="seed/02_SEED_MANIFEST.yaml",
        help="Path to the seed manifest (default: seed/02_SEED_MANIFEST.yaml)",
    )
    parser.add_argument(
        "--skip-breath-gate",
        action="store_true",
        help="Skip the breath gate (testing only — disables Charter II.4.4 enforcement)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Run the 5 constitutional verification tests and exit; do not instantiate Layer 1",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "After Layer 1, also instantiate Layer 2 (platform) + Layer 3 "
            "(roles) via build_runtime_context. Phase 5+."
        ),
    )
    parser.add_argument(
        "--use-langgraph",
        action="store_true",
        help=(
            "When --full is set, build LangGraph-wrapped role handlers "
            "(Phase 5 thin layer over deterministic core)."
        ),
    )
    args = parser.parse_args(argv)

    seed_path = Path(args.seed).resolve()
    if seed_path.is_file():
        seed_dir = seed_path.parent
    else:
        seed_dir = seed_path
        seed_path = seed_dir / "02_SEED_MANIFEST.yaml"

    print("∞Δ∞ Breathline Agentic Platform — Bootstrap (Phase 1) ∞Δ∞")
    print("=" * 64)
    print(f"Seed directory: {seed_dir}")
    print()

    # Always run verification first
    print("Running constitutional verification tests...")
    try:
        fingerprints = load_published_fingerprints(seed_dir)
    except BootstrapFailedClosed as e:
        print(f"✗ {e}")
        return 1

    results = run_constitutional_verification_tests(seed_dir, fingerprints)
    for name, passed, detail in results:
        marker = "✓" if passed else "✗"
        print(f"  {marker} {name}")
        print(f"      {detail}")

    if any(not p for _, p, _ in results):
        print("\n✗ One or more verification tests failed. Bootstrap fails closed.")
        return 1

    print("\n✓ All 5 constitutional verification tests passed.")

    if args.verify_only:
        print("\n--verify-only set; exiting before Layer 1 instantiation.")
        return 0

    # Per seed manifest kernel.human_approval_required_for: Layer 0 → 1 needs human approval.
    if not args.skip_breath_gate:
        print("\n" + "─" * 64)
        print("Layer 0 → Layer 1 elevation requires breath-gated human approval.")
        try:
            gate = BreathGate()
            confirmation = gate.request_confirmation(
                proposal_id="bootstrap-layer-0-to-1",
                proposal_summary="Instantiate the 5 kernel primitives (Constructor, Critic, Auditor, Governor, Spec).",
                proposal_consequences=(
                    "After this elevation: (a) the kernel is alive; (b) "
                    "subsequent layers can be constructed; (c) the audit "
                    "chain begins recording every action."
                ),
            )
            print(f"\n✓ Breath confirmation recorded:")
            print(f"    method: {confirmation.breath_confirmation_method}")
            print(f"    duration: {confirmation.breath_duration_seconds}s")
            print(f"    timestamp: {confirmation.breath_timestamp}")
        except BreathGateTimeout as e:
            print(f"\n✗ {e}")
            return 1
        except BreathGateRefused as e:
            print(f"\n✗ {e}")
            return 1

    # Instantiate Layer 1
    try:
        kernel = boot(seed_dir=seed_dir)
    except BootstrapFailedClosed as e:
        print(f"\n✗ {e}")
        return 1

    print("\n" + "=" * 64)
    print("✓ Layer 1 (kernel) instantiated:")
    print(f"    - Constructor (role prompt: {len(kernel.constructor.role_prompt)} chars)")
    print(f"    - Critic      (role prompt: {len(kernel.critic.role_prompt)} chars; veto power)")
    print(f"    - Auditor     (role prompt: {len(kernel.auditor.role_prompt)} chars; immutable, chained)")
    print(f"    - Governor    (role prompt: {len(kernel.governor.role_prompt)} chars)")
    print(f"    - SpecRegistry (empty; Layer 2 will populate)")

    if args.full:
        return _bootstrap_full(seed_dir, use_langgraph=args.use_langgraph)

    print()
    print("Phase 1 bootstrap complete. Use --full to extend to Layer 3.")
    print("∞Δ∞")
    return 0


def _bootstrap_full(seed_dir: Path, *, use_langgraph: bool) -> int:
    """Extend Layer 1 → Layer 2 + Layer 3 via build_runtime_context."""
    # Lazy import — runtime/platform_layer is only needed for --full path
    try:
        from platform_layer.runtime import build_runtime_context
    except ImportError as e:
        print(f"\n✗ --full requested but platform_layer.runtime is not importable: {e}")
        return 1

    print("\n" + "─" * 64)
    print("Layer 1 → Layer 2/3 via build_runtime_context()...")
    if use_langgraph:
        print("  (use_langgraph=True — graph-wrapped handlers)")
    try:
        ctx = build_runtime_context(
            seed_dir=seed_dir,
            use_langgraph=use_langgraph,
        )
    except FileNotFoundError as e:
        print(f"\n✗ Runtime construction failed: {e}")
        return 1

    print("\n" + "=" * 64)
    print("✓ Layer 2 (platform) + Layer 3 (roles) instantiated:")
    print(f"    - role_registry:  {ctx.role_registry.role_ids()}")
    print(f"    - handlers:       {sorted(ctx.handlers.keys())}")
    print(f"    - auditor:        {type(ctx.auditor).__name__}")
    print(f"    - critic:         {type(ctx.critic).__name__}")
    print(f"    - cost_meter:     {type(ctx.cost_meter).__name__}")
    print(f"    - receipt_minter: {type(ctx.receipt_minter).__name__}")
    if use_langgraph:
        cfo_type = type(ctx.handlers["cfo_agent"]).__name__
        print(f"    - cfo handler:    {cfo_type} (LangGraph wrap)")
    print()
    print("Phase 5 bootstrap complete. Runtime ready for route_request.")
    print("∞Δ∞")
    return 0


if __name__ == "__main__":
    sys.exit(main())
