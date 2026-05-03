# ADR-001: Coordinate Frame for Phase 1 Dynamics

## Status

Accepted

## Context

Conflict geometry in low-altitude terminal operations requires a local Cartesian form
to keep vector math compact and deterministic.

## Decision

Use a tangent-plane ENU projection centered at a configured aerodrome reference
point for all in-memory computations.

## Rationale

- Closed-form pair kinematics are simpler in Cartesian coordinates.
- WGS-84 to ENU conversion is deterministic and suitable for synthetic and replay
  data under ~50 NM terminal radii.
- A fallback full-ECEF path is kept available if needed for far-field scenarios.

## Consequences

- Every incoming surveillance state must be normalized into ENU before conflict math.
- Aerodrome reference and conversion behavior are pinned through `VCAS_AERODROME_*`
  environment settings and tested in `tests/test_grid.py` / `tests/test_physics_core.py`.
