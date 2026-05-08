"""The five primitive agents that constitute Layer 1 of the platform.

Per IMPLEMENTATION_PLAN.md Section 1, these primitives are reused unchanged
when adding new roles. Their prompts and behavior are byte-immutable from
the seed manifest at boot time; the Governor refuses any elevation that
would modify them.
"""

from kernel.primitives.spec import Spec, SpecKind, SpecRegistry
from kernel.primitives.constructor import Constructor, ConstructorRefusal
from kernel.primitives.critic import Critic, CriticVerdict
from kernel.primitives.auditor import Auditor, CylinderID
from kernel.primitives.governor import Governor, GovernorVerdict, ElevationDenied

__all__ = [
    "Spec",
    "SpecKind",
    "SpecRegistry",
    "Constructor",
    "ConstructorRefusal",
    "Critic",
    "CriticVerdict",
    "Auditor",
    "CylinderID",
    "Governor",
    "GovernorVerdict",
    "ElevationDenied",
]
