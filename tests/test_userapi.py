# -*- coding: utf-8 -*-
"""Test module for user API for ecl2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import ecl2df

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_userapi():
    """Test that we can act as human API user

    Functionality should be extensively tested in other code, but this is here
    to illustrate how a user could work, and ensure that it works.

    To the user reading the source: Skip all 'assert' lines, read the rest.

    """
    ef = ecl2df.EclFiles(DATAFILE)

    grid_df = ecl2df.grid.df(ef)
    grst_df = ecl2df.grid.df(ef, rstdates="last")
    nnc = ecl2df.nnc.df(ef)
    rft = ecl2df.rft.df(ef)
    smry = ecl2df.summary.df(ef)
    wcon = ecl2df.wcon.df(ef)
    compdatdf = ecl2df.compdat.df(ef)
    equil = ecl2df.equil.df(ef)
    gruptree = ecl2df.gruptree.df(ef)

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

    assert not nnc.empty
    assert not rft.empty
    assert not wcon.empty
    assert not smry.empty
    assert not compdatdf.empty
    assert not equil.empty
    assert not gruptree.empty
