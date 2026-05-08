"""Family CFO frameworks.

The FORECAST framework is reused from cfo_agent.frameworks.forecast —
the deterministic numeric core does not need narrowing.  Family-tier
narrowing happens at the role-handler level (FamilyCFOAgent.process)
and at the role_spec.yaml PermissionSpec level (allowed_action_classes,
breath_gate_thresholds).

This module is a placeholder marking the runtime path; family-specific
forecast extensions (e.g., household milestone tracking) land here as
the family series matures.
"""
