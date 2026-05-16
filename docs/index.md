# vCAS Testbed

Vector-based conflict alert system testbed for deterministic simulation, replay, audit, and visualization.

## System Surfaces

- FastAPI runtime under `src/vcas/api/`
- Core engine, geometry, risk, and audit logic under `src/vcas/`
- Browser radar/globe surfaces under `web/`
- Streamlit dashboard under `dashboard/`
- Canonical scenarios under `scenarios/canonical/`
- Monitoring templates under `monitoring/`

## Evidence

- Regression tests in `tests/`
- Build checkpoint in `BUILD_STATE.md`
- Demo parameter reference in `docs/demo_parameter_reference.md`
- Architecture decision records in `docs/adr/`
- Knowledge bank in `docs/wiki/vcas_knowledge_bank.md`

## Boundaries

This is a simulation testbed. Replay mode, external credentials, and deployment scaffolds are documented as runtime options, not mandatory local requirements.
