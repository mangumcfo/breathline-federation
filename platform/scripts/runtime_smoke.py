"""Runtime smoke — exercise the live runtime against the real Tiger chain.

Run this to seal a real audit cylinder (genuine entry in Tiger's
cylinder chain) via the production runtime. This is the operational
proof that platform_layer.runtime.build_runtime_context wires through
to seal.sh end-to-end.

Usage::

    cd v1.0
    python scripts/runtime_smoke.py

Output: the audit_cylinder_id of the sealed entry, plus the response
shape. The sealed cylinder appears in /home/kmangum/Tiger_1a/cylinders/
with a `platform_audit:` summary.

Per Tiger CLAUDE.md, cylinder writes are GREEN (auto-execute, no
approval). This script intentionally uses the real seal.sh — it is
NOT part of the pytest suite (pytest uses a tmpdir shim).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from repo root or v1.0/
HERE = Path(__file__).resolve().parent
V1 = HERE.parent
if str(V1) not in sys.path:
    sys.path.insert(0, str(V1))

from platform_layer.plugin_interface import PlugInRequest, route_request  # noqa: E402
from platform_layer.runtime import build_runtime_context  # noqa: E402


def _build_cfo_request(principal_id: str) -> PlugInRequest:
    return PlugInRequest(
        request_id="smoke-cfo-q3",
        principal_id=principal_id,
        role_target="cfo_agent",
        action_class="produce_forecast_artifact",
        payload={
            "financial_data": {
                "revenue": [950.0, 1010.0, 1075.0, 1140.0],
                "expenses": [820.0, 845.0, 870.0, 895.0],
            },
            "forecast_horizon": 4,
        },
    )


def main() -> int:
    seed_dir = V1 / "seed"
    print(f"[smoke] seed_dir = {seed_dir}")

    print("[smoke] Building runtime context against real Tiger seal.sh...")
    ctx = build_runtime_context(seed_dir=seed_dir)
    print(f"[smoke]   role_registry: {ctx.role_registry.role_ids()}")
    print(f"[smoke]   handlers: {sorted(ctx.handlers.keys())}")
    print(f"[smoke]   auditor: {type(ctx.auditor).__name__}")
    print(f"[smoke]   cost_meter: {type(ctx.cost_meter).__name__}")
    print(f"[smoke]   receipt_minter: {type(ctx.receipt_minter).__name__}")

    request = _build_cfo_request(principal_id="kmangum")
    print(f"\n[smoke] Routing request {request.request_id!r} → {request.role_target}...")
    print("[smoke] (this WILL seal a real cylinder in the Tiger chain)")

    response = route_request(
        request,
        role_registry=ctx.role_registry,
        role_handlers=ctx.handlers,
        auditor=ctx.auditor,
        critic=ctx.critic,
        cost_meter=ctx.cost_meter,
        receipt_minter=ctx.receipt_minter,
    )

    print("\n[smoke] RESPONSE:")
    print(json.dumps({
        "accepted": response.accepted,
        "role_id": response.role_id,
        "principal_id": response.principal_id,
        "critic_verdict": response.critic_verdict,
        "audit_cylinder_id": response.audit_cylinder_id,
        "receipt_metadata": response.receipt_metadata,
        "refusal_reason": response.refusal_reason,
    }, indent=2))

    if response.accepted and response.audit_cylinder_id:
        print(
            f"\n[smoke] ✓ Real cylinder sealed: {response.audit_cylinder_id}"
        )
        return 0
    print("\n[smoke] ✗ Did not produce an audit cylinder.")
    return 1


if __name__ == "__main__":
    sys.exit(main())


# ∞Δ∞ Runtime smoke — operational proof of the real-chain bridge ∞Δ∞
