from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from bingbong.core import compute_pop_count


@given(hour=st.integers(min_value=0, max_value=10_000))
def test_compute_pop_count_on_hour_property(hour: int) -> None:
    pops, chime = compute_pop_count(0, hour)
    assert chime is True
    assert pops == (hour % 12 or 12)


@given(
    minute=st.integers(min_value=0, max_value=59).filter(lambda m: m not in {0, 15, 30, 45}),
    hour=st.integers(min_value=0, max_value=23),
)
def test_compute_pop_count_non_quarter_is_silent(minute: int, hour: int) -> None:
    pops, chime = compute_pop_count(minute, hour)
    assert pops == 0
    assert chime is False
