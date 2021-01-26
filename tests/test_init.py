"""Check that ecl2df's submodules are always imported"""
import sys

# This file tests what happens when we do this import:
import ecl2df


def test_init():
    assert "ecl2df.compdat" in sys.modules

    # This should be a list of all submodules
    assert ecl2df.SUBMODULES

    for submodule in ecl2df.SUBMODULES:
        assert "ecl2df." + submodule in sys.modules

    # The Eclfiles object inside eclfiles should be lifted up to top-level:
    assert hasattr(ecl2df, "EclFiles")

    assert isinstance(ecl2df.__version__, str)
