# ADR-004: Risk Score Architecture and Floor Rule

## Status

Accepted

## Context

Task 4.9 requires an ML contribution without allowing model output to undercut
deterministic physics. The design needs deterministic safety first and graceful
operation when ML is unavailable.

## Decision

- `p_ml` is an async client that sends model feature windows to the ML endpoint
  and applies a circuit-breaker policy on failures/timeouts.
- Deterministic scoring uses:  
  `P_total = max(P_phys, w_fp·P_fp + w_phys·P_phys + w_ml·P_ml)`.
- If ML is disabled or unhealthy, `P_ml` falls back to `0.0`.

## Alternatives Considered

- Pure deterministic only scoring (`P_ml = 0` always): rejected because task 4.7/4.9
  requires a pluggable LSTM pathway.
- Unbounded ML override of physics: rejected because it can weaken safety
  invariants under false negatives.
- No circuit-breaker / no fallback: rejected due to known service flakiness in
  containerized/air-gapped environments.

## Consequences

- Thread 2A/2B always receive a valid `P_ml` vector and do not block on ML
  outages.
- Monitoring sees explicit ML request and failure counters for alerting and
  observability.
- Operators can run deterministic-only mode with `VCAS_ML_ENABLED=false`.

## Validation

- `src/vcas/risk/ml_client.py` exports async `p_ml` with breaker thresholds and
  deterministic fallback.
- Thread 2 pipelines consume `p_ml` through the same feature matrix path.
