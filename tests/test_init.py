"""Check that res2df's submodules are always imported"""

import sys

# This file tests what happens when we do this import:
import res2df


def test_init():
    """Test the top level properties of the res2df package"""
    assert "res2df.compdat" in sys.modules

    # This should be a list of all submodules
    assert res2df.SUBMODULES

    for submodule in res2df.SUBMODULES:
        assert "res2df." + submodule in sys.modules

    # The Eclfiles object inside resdatafiles should be lifted up to top-level:
    assert hasattr(res2df, "ResdataFiles")

    assert isinstance(res2df.__version__, str)
