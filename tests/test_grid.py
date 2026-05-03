# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from src.vcas.index import GridIndex, GridIndexConfig
from src.vcas.physics import AircraftState


def _state(callsign: str, x: float, y: float, z: float) -> AircraftState:
    return AircraftState(
        callsign=callsign,
        icao24=f"ICAO-{callsign}",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        alt_m=0.0,
        position_m=np.array([x, y, z], dtype=float),
        velocity_mps=np.array([0.0, 0.0, 0.0], dtype=float),
    )


def test_candidate_pairs_local_cluster():
    grid = GridIndex(GridIndexConfig(cell_size_m=1000.0))
    grid.insert(_state("AA01", 0, 0, 0))
    grid.insert(_state("AA02", 100, 100, 0))
    grid.insert(_state("AA03", 3000, 3000, 0))
    pairs = grid.candidate_pairs()
    assert len(pairs) == 1
    assert pairs[0] == ("AA01", "AA02")


def test_update_and_remove():
    grid = GridIndex(GridIndexConfig(cell_size_m=1000.0))
    grid.insert(_state("AA10", 0, 0, 0))
    grid.insert(_state("AA11", 1500, 0, 0))
    assert grid.total_states() == 2
    grid.update(_state("AA10", 1505, 0, 0))
    assert grid.total_states() == 2
    pairs = grid.candidate_pairs()
    assert ("AA10", "AA11") in pairs
    grid.remove("AA11")
    assert grid.total_states() == 1
    assert grid.candidate_pairs() == []
