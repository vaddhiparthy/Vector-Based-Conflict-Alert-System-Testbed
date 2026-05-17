# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Composite risk combination and bucket mapping."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BucketResult:
    value: float
    bucket: str


def composite_probability(
    p_phys: float,
    p_fp: float,
    p_ml: float,
    *,
    w_fp: float,
    w_phys: float,
    w_ml: float,
) -> float:
    weighted = w_fp * p_fp + w_phys * p_phys + w_ml * p_ml
    return float(max(p_phys, weighted))


def bucket_for(probability: float, *, tc_s: float) -> str:
    if tc_s < 120.0:
        return "high"
    if probability >= 0.70:
        return "high"
    if probability >= 0.50:
        return "medium"
    return "low"
