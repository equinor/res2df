"""Test module for satfunc2df"""

from ecl2df import inferdims


def test_injectsatnumcount():
    """Test that we always get out a string with TABDIMS"""
    assert "TABDIMS" in inferdims.inject_dimcount("", "TABDIMS", 0, 0)
    assert "TABDIMS" in inferdims.inject_dimcount("", "TABDIMS", 0, 1)
    assert "TABDIMS" in inferdims.inject_dimcount("TABDIMS", "TABDIMS", 0, 1)
    assert "99" in inferdims.inject_dimcount("", "TABDIMS", 0, 99)

    assert " 1* " in inferdims.inject_dimcount("", "TABDIMS", 1, 99)
    assert "*" not in inferdims.inject_dimcount("", "TABDIMS", 0, 99)

    assert "EQLDIMS" in inferdims.inject_dimcount("", "EQLDIMS", 0, 0)
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
