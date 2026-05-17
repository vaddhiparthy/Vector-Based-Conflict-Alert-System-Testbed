# ADR-007: Flight Plan and Wind Integration

## Status

Accepted

## Context

Phase 7 requires conflict projection to account for planned trajectories and environmental
effects. Previous conflict screening in vCAS only compared current kinematic states and
static separation thresholds, which did not capture route intent, and used raw frame-reported
groundspeed vectors without a wind correction term.

## Decision

- Add a 4D flight-plan model (`FlightPlan`, `FlightWaypoint`) with interpolation helpers.
- Generate synthetic plans from scenario definitions using deterministic kinematic sampling.
- Derive replay plans from track history by sampling recorded timestamps.
- Expand flight-plan risk to use scheduled trajectory proximity and recent actual-vs-planned
  deviation over a rolling window.
- Introduce a configurable wind profile model with altitude bands and apply it during state
  conversion so that downstream trajectory prediction and screening use wind-adjusted
  velocities.

## Alternatives Considered

- Continue with state-only screening and ignore flight intent:
  rejected because it misses known route-capture effects and causes unstable alerts for
  high-variance tracks.
- Use live weather APIs per-frame:
  rejected due to external dependency cost and deterministic replay constraints.
- Use stochastic trajectory forecasts:
  rejected at this stage to preserve deterministic behavior for baseline scorecards.

## Consequences

- `engine` now carries flight plans through Thread 1 candidates and Thread 2 risk scoring.
- New `wind.yaml` configuration defines deterministic testbed wind with altitude bands.
- Forecast-like risk now includes both scheduled crossing and route-adherence signals.
- Deterministic replay and synthetic smoke tests can be calibrated and compared via unit tests.

## Validation

- `tests/test_flight_plan.py` covers synthetic plan generation, replay plan derivation, and
  risk outputs with and without plan context.
- `src/vcas/wind/model.py`, `src/vcas/surveillance/adapter.py`, and `src/vcas/core/engine.py`
  are integrated for plan propagation and wind-adjusted velocities.
