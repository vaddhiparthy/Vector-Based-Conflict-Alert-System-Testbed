# ADR-006: Visualization Stack Choice

## Status

Accepted

## Context

vCAS visualization required a browser-native 3D view that could render aircraft
entities, labels, conflict pairs, and protected geometry while staying consistent
with the IP posture for the demo stack.

## Decision

Use CesiumJS for the web globe path in this phase.

## Alternatives Considered

- Mapbox GL JS: strong mapping surface but weaker native air-traffic workflows
  compared with Cesium’s globe-first 3D model.
- deck.gl: excellent geospatial rendering primitives, but required deeper custom
  aviation-specific scene/state scaffolding for this scope.
- three.js: flexible low-level control but high implementation cost to reproduce
  globe, camera, and camera-relative semantics consistently.

## Consequences

- Front-end work must keep a Cesium-ready render path and include attribution
  and author framing for the dashboard narrative.
- The current lightweight static demo remains a functional fallback while this
  branch of work continues.
- Future WebGL or map-provider substitution should include migration notes for
  coordinate ingest and entity lifecycle parity.

## Validation

- Task 6.11 completed Streamlit controller + replay scrubber.
- Task 6.12 completed run/scrub interface in dashboard and web UI entry path.
- Task 6.13 completed audit drill-down visibility and row-chain tracing.
- Task 6.14 adds a deterministic performance benchmark script to validate frame
  throughput under synthetic 200-aircraft load.
