"""Test module for satfunc2df"""
import re

import pytest

from ecl2df import inferdims

try:
    import opm  # noqa
except ImportError:
    pytest.skip(
        "OPM is not installed, nothing relevant in here then",
        allow_module_level=True,
    )


def test_injectsatnumcount():
    """Test that we always get out a string with TABDIMS"""
    assert "TABDIMS" in inferdims.inject_dimcount("", "TABDIMS", 0, 1)
    assert "TABDIMS" in inferdims.inject_dimcount("", "TABDIMS", 0, 1)
    assert "TABDIMS" in inferdims.inject_dimcount("TABDIMS", "TABDIMS", 0, 1)
    assert "99" in inferdims.inject_dimcount("", "TABDIMS", 0, 99)

    assert " 1* " in inferdims.inject_dimcount("", "TABDIMS", 1, 99)
    assert "*" not in inferdims.inject_dimcount("", "TABDIMS", 0, 99)

    assert "EQLDIMS" in inferdims.inject_dimcount("", "EQLDIMS", 0, 1)
    assert "EQLDIMS" in inferdims.inject_dimcount("", "EQLDIMS", 0, 1)
    assert "EQLDIMS" in inferdims.inject_dimcount("EQLDIMS", "EQLDIMS", 0, 1)
    assert "99" in inferdims.inject_dimcount("", "TABDIMS", 0, 99)


def test_guess_ntequil():
    """Test inferring the correct NTEQUIL"""
    assert inferdims.guess_dim("EQUIL\n200 2000/\n2000 2000/\n", "EQLDIMS", 0) == 2
    assert inferdims.guess_dim("EQUIL\n200 2000/\n", "EQLDIMS", 0) == 1
    assert inferdims.guess_dim("EQUIL\n200 2000 333/\n0 0/\n1 1/\n", "EQLDIMS", 0) == 3


def test_guess_satnumcount():
    """Test that we are able to guess the SATUM count in difficult cases"""
    # We always require a newline after a "/" in the Eclipse syntax
    # (anything between a / and \n is ignored)
    assert inferdims.guess_dim("SWOF\n0/\n0/\n", "TABDIMS", 0) == 2
    assert inferdims.guess_dim("SWOF\n0/\n0/ \n0/\n", "TABDIMS", 0) == 3
    assert inferdims.guess_dim("SWFN\n0/\n\n0/\n", "TABDIMS", 0) == 2
    assert inferdims.guess_dim("SGOF\n0/\n", "TABDIMS", 0) == 1
    assert inferdims.guess_dim("SGOF\n0/\n0/\n", "TABDIMS", 0) == 2
    assert inferdims.guess_dim("SGOF\n0/\n0/\n0/\n", "TABDIMS", 0) == 3
    assert (
        inferdims.guess_dim("SGOF\n0 0 0 0/\n0 0 0 0/\n0 0 0 0/\n", "TABDIMS", 0) == 3
    )
    assert (
        inferdims.guess_dim(
            "SGOF\n0 0 0 0 1 1 1 1/\n0 0 0 0 1 1 1 1/\n0 0 0 0 1 1 1/\n", "TABDIMS", 0
        )
        == 3
    )


def test_guess_dim():
    """Test error conditions"""
    with pytest.raises(ValueError, match="Only supports TABDIMS and EQLDIMS"):
        inferdims.guess_dim("SWOF\n0/\n0/\n", "WELLDIMS", 0)

    with pytest.raises(ValueError, match="Only support item 0 and 1 in TABDIMS"):
        inferdims.guess_dim("SWOF\n0/\n0/\n", "TABDIMS", 2)

    with pytest.raises(ValueError, match="Only item 0 in EQLDIMS can be estimated"):
        inferdims.guess_dim("EQUIL\n0/\n0/\n", "EQLDIMS", 1)


def test_inject_dimcount():
    """Test error conditions"""
    with pytest.raises(ValueError, match="Only supports TABDIMS and EQLDIMS"):
        inferdims.inject_dimcount("SWOF\n0/\n0/\n", "WELLDIMS", 0, 1)

    with pytest.raises(ValueError, match="Only support item 0 and 1 in TABDIMS"):
        inferdims.inject_dimcount("SWOF\n0/\n0/\n", "TABDIMS", 2, 1)

    with pytest.raises(ValueError, match="Only item 0 in EQLDIMS can be injected"):
        inferdims.inject_dimcount("EQUIL\n0/\n0/\n", "EQLDIMS", 1, 1)

    with pytest.raises(AssertionError, match="dimvalue must be larger than zero"):
        inferdims.inject_dimcount("SWOF\n0/\n0/\n", "TABDIMS", 1, 0, 0)


def test_inject_xxxdims_ntxxx():
    """Test the wrapper of inject_dimcount()"""

    with pytest.raises(AssertionError):
        inferdims.inject_xxxdims_ntxxx("WELLDIMS", "NTSFUN", "SWOF\n0/\n0/\n")
    with pytest.raises(AssertionError):
        inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTFUN", "SWOF\n0/\n0/\n")

    # Repeated calls should be ok:
    deck_with_injection = inferdims.inject_xxxdims_ntxxx(
        "TABDIMS", "NTSFUN", "SWOF\n0/\n0/\n", 1
    )

    assert "TABDIMS\n 1 /" in re.sub(
        " +",
        " ",
        str(
            inferdims.inject_xxxdims_ntxxx(
                "TABDIMS", "NTSFUN", deck_with_injection, None
            )
        ),
    )
    # If no number is supplied, return the deck untouched:
    assert "TABDIMS\n 1 /" in re.sub(
        " +",
        " ",
        str(
            inferdims.inject_xxxdims_ntxxx(
                "TABDIMS", "NTSFUN", deck_with_injection, None
            )
        ),
    )
