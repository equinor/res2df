"""Test module for user API for ecl2df"""

from pathlib import Path

import pytest

import ecl2df

try:
    import opm  # noqa

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


@pytest.mark.skipif(not HAVE_OPM, reason="Test requires OPM")
def test_userapi():
    """Test that we can act as human API user

    Functionality should be extensively tested in other code, but this is here
    to illustrate how a user could work, and ensure that it works.

    To the user reading the source: Skip all 'assert' lines, read the rest.

    """
    eclfiles = ecl2df.EclFiles(REEK)

    compdatdf = ecl2df.compdat.df(eclfiles)
    equil = ecl2df.equil.df(eclfiles)
    faults = ecl2df.faults.df(eclfiles)
    fipreports = ecl2df.fipreports.df(eclfiles)
    grid_df = ecl2df.grid.df(eclfiles)
    grst_df = ecl2df.grid.df(eclfiles, rstdates="last")
    gruptree = ecl2df.gruptree.df(eclfiles)
    nnc = ecl2df.nnc.df(eclfiles)
    pillars = ecl2df.pillars.df(eclfiles)
    rft = ecl2df.rft.df(eclfiles)
    satfunc = ecl2df.satfunc.df(eclfiles)
    smry = ecl2df.summary.df(eclfiles, datetime=True)
    trans = ecl2df.trans.df(eclfiles)
    wcon = ecl2df.wcon.df(eclfiles)

    assert "PORV" in grid_df
    assert "SOIL" not in grid_df
    assert "SOIL" in grst_df
    assert "PORV" in grst_df

    # Make some HCPV calculations
    grst_df["OILPV"] = grst_df["SOIL"] * grst_df["PORV"]
    grst_df["HCPV"] = (1 - grst_df["SWAT"]) * grst_df["PORV"]

    hcpv_table = grst_df.groupby("FIPNUM").sum()[["OILPV", "HCPV"]]
    assert not hcpv_table.empty

    # Print the HCPV table by FIPNUM:
    print()
    print((hcpv_table / 1e6).round(2))

    assert not compdatdf.empty
    assert not equil.empty
    assert not faults.empty
    assert not fipreports.empty
    assert not gruptree.empty
    assert not nnc.empty
    assert not pillars.empty
    assert not rft.empty
    assert not satfunc.empty
    assert not smry.empty
    assert not trans.empty
    assert not wcon.empty
