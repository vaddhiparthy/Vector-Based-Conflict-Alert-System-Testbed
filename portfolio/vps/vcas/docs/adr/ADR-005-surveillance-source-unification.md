# ADR-005: Three-Source Surveillance Architecture

## Status

Accepted

## Context

vCAS must ingest from synthetic, replay, and simulated sources while keeping a
single downstream processing contract.

## Decision

- Use one `SurveillanceFrame` schema for all sources.
- Preserve a single adapter entry-point in `surveillance.adapter` and return one
  normalized iterable of frames.
- Keep source-specific loaders behind `build_prepared_frames(settings)` dispatch:
  `synthetic`, `replay`, and `simulator`.
- Derive flight plans from synthetic and replay sources at run time so thread 2
  scoring receives trajectory context.

## Alternatives Considered

- Separate pipelines per source with duplicated ingestion and state updates:
  rejected because it duplicates normalization, plan derivation, and audit behavior.
- Only synthetic/replay support: rejected because the phase requires a simulator
  path for public demo and validation.

## Consequences

- API run endpoints can switch source via `source_mode`.
- Replay and synthetic determinism can be compared via normalized frame streams.
- New simulator scenarios in `scenarios/bluesky/*.yml` can be consumed
  without additional application plumbing.

## Validation

- `surveillance.adapter` exposes source-specific builders with a shared return type.
- `surveillance.simulator.bluesky_runner` emits deterministic frames for BlueSky
  scenario YAML files.
- `build_prepared_frames` controls all source-mode entry to the engine.
