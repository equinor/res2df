from pathlib import Path

import pytest

import res2df


@pytest.fixture
def path_to_res2df():
    """Path to installed res2df module"""
    return Path(res2df.__file__).parent
