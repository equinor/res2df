from pathlib import Path

import pytest

import ecl2df


@pytest.fixture
def path_to_ecl2df():
    """Path to installed ecl2df module"""
    return Path(ecl2df.__file__).parent
