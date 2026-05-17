# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Uniform 3D grid index for candidate-pair generation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from ..physics.state import AircraftState


Cell = Tuple[int, int, int]
Pair = Tuple[str, str]


@dataclass(frozen=True)
class GridIndexConfig:
    cell_size_m: float


class GridIndex:
    """A lightweight cell-indexed neighbor registry for ENU states."""

    def __init__(self, config: GridIndexConfig):
        if config.cell_size_m <= 0:
            raise ValueError("cell_size_m must be positive")
        self.config = config
        self._cell_to_callsigns: Dict[Cell, Set[str]] = defaultdict(set)
        self._call_to_cell: Dict[str, Cell] = {}
        self._states: Dict[str, AircraftState] = {}

    def _cell_of(self, xyz: np.ndarray) -> Cell:
        cell = tuple((xyz / self.config.cell_size_m).astype(int))
        return int(cell[0]), int(cell[1]), int(cell[2])

    def insert(self, state: AircraftState) -> None:
        key = state.normalized_callsign()
        if not key:
            raise ValueError("state.callsign required")
        cell = self._cell_of(state.position_m)
        self._cell_to_callsigns[cell].add(key)
        self._call_to_cell[key] = cell
        self._states[key] = state

    def update(self, state: AircraftState) -> None:
        key = state.normalized_callsign()
        if not key:
            raise ValueError("state.callsign required")
        if key in self._call_to_cell:
            self.remove(key)
        self.insert(state)

    def remove(self, callsign: str) -> Optional[AircraftState]:
        key = callsign.strip().upper()
        if key not in self._call_to_cell:
            return None
        old_cell = self._call_to_cell.pop(key)
        self._cell_to_callsigns[old_cell].discard(key)
        if not self._cell_to_callsigns[old_cell]:
            del self._cell_to_callsigns[old_cell]
        return self._states.pop(key, None)

    def state(self, callsign: str) -> Optional[AircraftState]:
        return self._states.get(callsign.strip().upper())

    def candidate_pairs(self) -> List[Pair]:
        pairs: Set[Pair] = set()
        for cell, callsigns in list(self._cell_to_callsigns.items()):
            cx, cy, cz = cell
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        neighbor = (cx + dx, cy + dy, cz + dz)
                        neighbor_calls = self._cell_to_callsigns.get(neighbor, set())
                        if not neighbor_calls:
                            continue
                        for left in callsigns:
                            for right in neighbor_calls:
                                if left >= right:
                                    continue
                                pairs.add((left, right))
        return sorted(pairs)

    def occupied_cells(self) -> int:
        return len(self._cell_to_callsigns)

    def total_states(self) -> int:
        return len(self._states)

    def clear(self) -> None:
        self._cell_to_callsigns.clear()
        self._call_to_cell.clear()
        self._states.clear()

    def snapshot(self) -> Tuple[int, int]:
        return self.total_states(), self.occupied_cells()
