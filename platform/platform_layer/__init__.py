"""Platform layer (Layer 2). Phase 2 fully populated.

Note on package naming: this directory is named ``platform_layer/`` (not
``platform/``) to avoid shadowing Python's stdlib ``platform`` module. The
IMPLEMENTATION_PLAN.md references ``platform/`` as the conceptual name; the
implementation uses ``platform_layer/`` for stdlib hygiene. All other
naming follows the plan exactly.

Phase 2 components:
  - audit_adapter      — synchronous seal.sh subprocess; fails closed
  - permission_spec    — Charter V.7 enforcement at instantiation
  - registry           — Spec registry (re-export) + Role registry
  - receipt_minter     — default-deny external B49 receipts; rate limiting
  - plugin_interface   — FastAPI; least-authority filtering BEFORE role reach
"""
from platform_layer.audit_adapter import AuditAdapter
from platform_layer.permission_spec import (
    ActionClassRegistry,
    PermissionSpec,
    PermissionSpecViolation,
    ActionClassUnknown,
    ActionClassForbidden,
    ActionClassOutsideEnvelope,
)
from platform_layer.registry import RoleRegistry, RegisteredRole, SpecRegistry, Spec
from platform_layer.receipt_minter import (
    ReceiptMinter,
    ReceiptMintRefused,
    ReceiptID,
    MintResult,
)
from platform_layer.plugin_interface import (
    PlugInRequest,
    PlugInResponse,
    route_request,
    create_app,
)

__all__ = [
    # audit_adapter
    "AuditAdapter",
    # permission_spec
    "ActionClassRegistry",
    "PermissionSpec",
    "PermissionSpecViolation",
    "ActionClassUnknown",
    "ActionClassForbidden",
    "ActionClassOutsideEnvelope",
    # registry
    "RoleRegistry",
    "RegisteredRole",
    "SpecRegistry",
    "Spec",
    # receipt_minter
    "ReceiptMinter",
    "ReceiptMintRefused",
    "ReceiptID",
    "MintResult",
    # plugin_interface
    "PlugInRequest",
    "PlugInResponse",
    "route_request",
    "create_app",
]
