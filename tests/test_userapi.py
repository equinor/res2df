"""Test module for user API for res2df"""

from pathlib import Path

import pytest

import res2df

try:
    # pylint: disable=unused-import
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
    resdatafiles = res2df.ResdataFiles(REEK)

    compdatdf = res2df.compdat.df(resdatafiles)
    equil = res2df.equil.df(resdatafiles)
    faults = res2df.faults.df(resdatafiles)
    fipreports = res2df.fipreports.df(resdatafiles)
    grid_df = res2df.grid.df(resdatafiles)
    grst_df = res2df.grid.df(resdatafiles, rstdates="last")
    gruptree = res2df.gruptree.df(resdatafiles)
    nnc = res2df.nnc.df(resdatafiles)
    pillars = res2df.pillars.df(resdatafiles)
    rft = res2df.rft.df(resdatafiles)
    satfunc = res2df.satfunc.df(resdatafiles)
    smry = res2df.summary.df(resdatafiles, datetime=True)
    trans = res2df.trans.df(resdatafiles)
    wcon = res2df.wcon.df(resdatafiles)

    assert "PORV" in grid_df
    assert "SOIL" not in grid_df
    assert "SOIL" in grst_df
    assert "PORV" in grst_df

    # Make some HCPV calculations
    grst_df["OILPV"] = grst_df["SOIL"] * grst_df["PORV"]
    grst_df["HCPV"] = (1 - grst_df["SWAT"]) * grst_df["PORV"]

    hcpv_table = grst_df.groupby("FIPNUM").sum()[["OILPV", "HCPV"]]
    assert not hcpv_table.empty

    # Create string with :term:`include file` contents for the HCPV table by FIPNUM:
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
