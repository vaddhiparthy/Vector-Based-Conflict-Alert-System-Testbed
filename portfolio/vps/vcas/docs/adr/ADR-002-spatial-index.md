# ADR-002: Spatial Index Strategy

## Status

Accepted

## Context

Naïve all-pairs comparison is O(n²) and breaks throughput requirements for 200+
aircraft at 1 Hz.

## Decision

Adopt a uniform 3D grid hash with neighbor enumeration for candidate-pair
generation in vCAS.

## Rationale

- Simple implementation with deterministic cell lookups.
- Efficient pruning for local terminal operating volumes.
- Easy introspection for explainability and debugging of performance behavior.

## Consequences

- Candidate generation becomes dependent on `cell_size_m`; this value is surfaced in
  `VCAS_CELL_SIZE_M`.
- Cells can be monitored for occupancy and candidate pressure via metrics.
