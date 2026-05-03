# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

from __future__ import annotations

import numpy as np

from vcas.geo.coords import EnuConverter, ReferencePoint


def test_enu_roundtrip_stays_close_to_input():
    converter = EnuConverter(
        ReferencePoint(
            latitude_deg=38.944,
            longitude_deg=-77.455,
            altitude_m=100.0,
        )
    )
    expected_lat = 38.952
    expected_lon = -77.440
    expected_alt = 300.0

    enu = converter.geodetic_to_enu(expected_lat, expected_lon, expected_alt)
    lat, lon, alt = converter.enu_to_geodetic(*enu)

    assert np.isclose(lat, expected_lat, atol=2e-5)
    assert np.isclose(lon, expected_lon, atol=2e-5)
    assert np.isclose(alt, expected_alt, atol=1e-2)
