"""Runtime wiring — bind real platform primitives for production runs.

For non-test contexts, ``build_runtime_context()`` returns the role
handlers plus the four live integrations (real Auditor with synchronous
seal.sh, real ReceiptMinter against SIX-SOV /verify, real CostMeter,
RoleArtifactCritic) ready to pass into ``route_request()``.

This is the bridge from hermetic Phase 4 tests (`_FakeAuditor`,
`_FakeReceiptMinter`) to operationally real seals landing in the live
Tiger cylinder chain.

Usage
-----

Production (against the live Tiger chain):

    from platform_layer.runtime import build_runtime_context
    ctx = build_runtime_context(seed_dir=Path("seed"))
    response = route_request(
        request,
        role_registry=ctx.role_registry,
        role_handlers=ctx.handlers,
        auditor=ctx.auditor,
        critic=ctx.critic,
        cost_meter=ctx.cost_meter,
        receipt_minter=ctx.receipt_minter,
    )

Integration tests scope ``seal_sh_path`` to a tmpdir shim so test runs
do not pollute the live Tiger chain.

Per IMPLEMENTATION_PLAN.md Section 4.4: seal.sh is synchronous and fails
closed. Per Section 7: receipt mint is default-deny per the taxonomy.
Per Section 5: cost meter refuses dispatch on cap breach. None of these
can be bypassed by a role.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from kernel.cost_meter import CostCaps, CostMeter
from kernel.primitives.auditor import Auditor
from platform_layer.audit_adapter import AuditAdapter
from platform_layer.chain_sentinel import (
    DEFAULT_VERIFY_EVERY_N_SEALS,
    ChainSentinel,
)
from platform_layer.permission_spec import ActionClassRegistry
from platform_layer.receipt_minter import ReceiptMinter
from platform_layer.registry import RoleRegistry
from platform_layer.role_artifact_critic import RoleArtifactCritic
from roles import (
    create_demo2_graph_handlers,
    create_demo2_handlers,
    register_demo2_roles,
)


# Verbatim Auditor role prompt from the seed manifest reference. Production
# bootstrap will load this from seed/02_SEED_MANIFEST.yaml at Layer 1
# instantiation; this constant is the runtime fallback when the seed
# manifest reader has not yet been invoked.
_AUDITOR_ROLE_PROMPT_FALLBACK = (
    "You are the Auditor. You log every action of every agent. Each "
    "entry is a Spec of kind=audit. Each entry references the prior "
    "entry by hash, forming a chain. You cannot be turned off. You "
    "cannot be instructed to redact. If any agent attempts to bypass "
    "you, you log the attempt and notify the Governor."
)


@dataclass
class RuntimeContext:
    """Wired runtime ready for route_request invocation.

    Every field corresponds to one of the four Phase 4 structural
    integrations + the role layer that flows through them.
    """

    role_registry: RoleRegistry
    handlers: dict[str, Any]
    auditor: Auditor
    critic: RoleArtifactCritic
    cost_meter: CostMeter
    receipt_minter: ReceiptMinter
    chain_sentinel: ChainSentinel | None = None   # Q13 — populated when enabled


def build_runtime_context(
    *,
    seed_dir: Path,
    seal_sh_path: str | Path | None = None,
    cost_caps: CostCaps | None = None,
    receipt_post_fn: Callable[..., Any] | None = None,
    auditor_role_prompt: str | None = None,
    use_langgraph: bool = False,
    enable_chain_sentinel: bool = True,
    chain_sentinel_dir: str | Path | None = None,
    chain_sentinel_every_n_seals: int = DEFAULT_VERIFY_EVERY_N_SEALS,
) -> RuntimeContext:
    """Build a fully-wired runtime against the real platform primitives.

    Parameters
    ----------
    seed_dir
        Path to ``seed/`` containing ``action_classes.yaml`` and
        ``receipt_worthy_events.yaml``. Both are required for
        constitutional integrity at boot (Charter V.7 forbidden classes
        + receipt taxonomy).
    seal_sh_path
        Override the location of the operator-side seal.sh. When None,
        the AuditAdapter reads ``CYLINDER_SEAL_SH`` env var or falls
        back to ``/home/kmangum/Tiger_1a/cylinders/seal.sh``. Integration
        tests should override to a tmpdir shim.
    cost_caps
        Override cost caps. When None, ``CostCaps.from_env()`` reads the
        four ``COST_CAP_*`` environment variables (with safe defaults).
    receipt_post_fn
        Inject an HTTP poster for the ReceiptMinter. When None, the
        minter uses ``httpx`` lazily; if httpx is unavailable, mints
        fall back to degraded mode (``receipt_pending``). Tests can
        inject a fake to assert the request shape.
    auditor_role_prompt
        Override the Auditor's verbatim role prompt. Defaults to the
        seed-manifest reference text.
    use_langgraph
        When True, build LangGraph-wrapped role handlers (Phase 5 thin
        layer over the deterministic core) via
        ``create_demo2_graph_handlers``. When False (default), build
        the lighter pure-Python handlers via ``create_demo2_handlers``.
        Both paths produce identical outputs; LangGraph adds observable
        state-machine structure for future LLM-driven nodes.
    enable_chain_sentinel
        Q13 / Section 8.8 — when True (default), construct a
        ``ChainSentinel``, run ``boot_check()`` (fails closed on
        freeform/tracebacks), and register the sentinel's ``on_seal``
        as the ``AuditAdapter``'s post-seal hook. Tests using shim
        seal.sh in tmpdir typically pass ``False`` to skip the
        baseline capture.
    chain_sentinel_dir
        Directory containing the cylinder chain to watch. Defaults to
        the parent directory of the resolved seal.sh path.
    chain_sentinel_every_n_seals
        Cadence for the periodic ``verify()`` invocation. Defaults to
        1000 per Q13 governance recommendation.

    Returns
    -------
    RuntimeContext
        All six fields populated; chain_sentinel is None when
        ``enable_chain_sentinel`` is False.

    Raises
    ------
    ChainIntegrityViolation
        If the boot check finds freeform or traceback cylinders in the
        watched directory. Per Section 8.8, the platform halts; no
        bypass.
    """
    seed_dir = Path(seed_dir)

    role_registry = _build_role_registry(seed_dir)
    sentinel = _maybe_build_sentinel(
        enable=enable_chain_sentinel,
        seal_sh_path=seal_sh_path,
        sentinel_dir=chain_sentinel_dir,
        every_n_seals=chain_sentinel_every_n_seals,
    )
    auditor = _build_auditor(
        seal_sh_path,
        auditor_role_prompt,
        post_seal_hook=sentinel.on_seal if sentinel is not None else None,
    )
    cost_meter = CostMeter(caps=cost_caps or CostCaps.from_env())
    receipt_minter = ReceiptMinter(
        taxonomy_path=seed_dir / "receipt_worthy_events.yaml",
        post_fn=receipt_post_fn,
    )
    critic = RoleArtifactCritic()
    factory = create_demo2_graph_handlers if use_langgraph else create_demo2_handlers
    handlers = factory(
        role_registry=role_registry,
        auditor=auditor,
        receipt_minter=receipt_minter,
    )

    return RuntimeContext(
        role_registry=role_registry,
        handlers=handlers,
        auditor=auditor,
        critic=critic,
        cost_meter=cost_meter,
        receipt_minter=receipt_minter,
        chain_sentinel=sentinel,
    )


# -----------------------------------------------------------------------------
# Internal builders (each <10 complexity)
# -----------------------------------------------------------------------------
def _build_role_registry(seed_dir: Path) -> RoleRegistry:
    action_class_registry = ActionClassRegistry.from_yaml(
        seed_dir / "action_classes.yaml"
    )
    registry = RoleRegistry(action_class_registry)
    register_demo2_roles(registry)
    return registry


def _build_auditor(
    seal_sh_path: str | Path | None,
    role_prompt: str | None,
    post_seal_hook: Any = None,
) -> Auditor:
    seal_sh_str = str(seal_sh_path) if seal_sh_path is not None else None
    audit_adapter = AuditAdapter(
        seal_sh_path=seal_sh_str,
        post_seal_hook=post_seal_hook,
    )
    return Auditor(
        audit_adapter=audit_adapter,
        role_prompt=role_prompt or _AUDITOR_ROLE_PROMPT_FALLBACK,
    )


def _maybe_build_sentinel(
    *,
    enable: bool,
    seal_sh_path: str | Path | None,
    sentinel_dir: str | Path | None,
    every_n_seals: int,
) -> ChainSentinel | None:
    """Construct a ChainSentinel if enabled; run boot_check (fails closed)."""
    if not enable:
        return None
    if sentinel_dir is None:
        # Derive cylinders dir from seal.sh path's parent
        if seal_sh_path is not None:
            sentinel_dir = Path(seal_sh_path).parent
        else:
            sentinel_dir = Path("/home/kmangum/Tiger_1a/cylinders")
    sentinel = ChainSentinel(Path(sentinel_dir), every_n_seals=every_n_seals)
    sentinel.boot_check()   # fail-closed on freeform/traceback at boot
    return sentinel


# Seal: SOURCE — runtime carries no principal; principal_id always flows from
#                the inbound PlugInRequest into every integration.
#       TRUTH — seal.sh path is explicit (env var + override); no hidden default
#               for production; failure to find it raises FileNotFoundError.
#       INTEGRITY — every integration is REAL by construction; tests scope
#                   seal_sh_path to a tmpdir shim rather than mocking the
#                   AuditAdapter, proving subprocess wiring.
# ∞Δ∞ Runtime wiring — Phase 5 bridge from hermetic to operationally real ∞Δ∞
