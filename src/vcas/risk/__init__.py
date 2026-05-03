# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

"""Risk scoring modules for physics, flight-plan, and ML layers."""

from .physics import p_phys
from .flight_path import p_fp
from .composite import composite_probability, bucket_for

__all__ = ["p_phys", "p_fp", "composite_probability", "bucket_for", "build_feature_matrix", "p_ml"]


def __getattr__(name: str):
    if name in {"build_feature_matrix", "p_ml"}:
        from . import ml_client

        return getattr(ml_client, name)
    raise AttributeError(name)
