# -*- coding: utf-8 -*-
"""Test module for ecl2df.grid"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import datetime
import pandas as pd

import pytest

from ecl2df import grid
from ecl2df import ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_gridgeometry2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    grid_geom = grid.gridgeometry2df(eclfiles)

    assert isinstance(grid_geom, pd.DataFrame)
    assert not grid_geom.empty

    assert "I" in grid_geom
    assert "J" in grid_geom
    assert "K" in grid_geom
    assert "X" in grid_geom
    assert "Y" in grid_geom
    assert "Z" in grid_geom
    assert "VOLUME" in grid_geom


def test_wrongfile():
    try:
        FileNotFoundError
    except NameError:
        FileNotFoundError = IOError

    # We can initalize this object with bogus:
    eclfiles = EclFiles("FOO.DATA")
    # but when we try to use it, things should fail:
    with pytest.raises(FileNotFoundError):
        grid.init2df(eclfiles)


def test_init2df():
    """Test that dataframe with INIT vectors can be produced"""
    eclfiles = EclFiles(DATAFILE)
    init_df = grid.init2df(eclfiles)

    assert isinstance(init_df, pd.DataFrame)
    assert not init_df.empty
    assert "PERMX" in init_df
    assert "PORO" in init_df
    assert "PORV" in init_df


def test_grid2df():
    """Test that dataframe with INIT vectors and coordinates can be produced"""
    eclfiles = EclFiles(DATAFILE)
    grid_df = grid.grid2df(eclfiles)

    assert isinstance(grid_df, pd.DataFrame)
    assert not grid_df.empty
    assert "PERMX" in grid_df
    assert "PORO" in grid_df
    assert "PORV" in grid_df
    assert "I" in grid_df
    assert "J" in grid_df
    assert "K" in grid_df
    assert "X" in grid_df
    assert "Y" in grid_df
    assert "Z" in grid_df
    assert "VOLUME" in grid_df


def test_transmissibilities():
    """Test that we can build a dataframe of transmissibilities"""
    eclfiles = EclFiles(DATAFILE)
    trans_df = grid.transdf(eclfiles)
    assert "TRAN" in trans_df
    assert "DIR" in trans_df
    assert set(trans_df["DIR"].unique()) == set(["I", "J", "K"])
    assert trans_df["TRAN"].sum() > 0

    # Try including some vectors:
    trans_df = grid.transdf(eclfiles, vectors="FIPNUM")
    assert "FIPNUM" not in trans_df
    assert "FIPNUM1" in trans_df
    assert "EQLNUM2" not in trans_df

    trans_df = grid.transdf(eclfiles, vectors=["FIPNUM", "EQLNUM"])
    assert "FIPNUM1" in trans_df
    assert "EQLNUM2" in trans_df

    trans_df = grid.transdf(eclfiles, vectors="BOGUS")
    assert "BOGUS1" not in trans_df
    assert "TRAN" in trans_df  # (we should have gotten a warning only)

    # Example creating a column with the FIPNUM pair as a string
    # (lowest fipnum value first)
    trans_df = grid.transdf(eclfiles, vectors=["X", "Y", "Z", "FIPNUM"])
    trans_df["FIPNUMPAIR"] = [
        str(int(min((x[1:3])))) + "-" + str(int(max(x[1:3])))
        for x in trans_df[["FIPNUM1", "FIPNUM2"]].itertuples()
    ]
    # Filter to different FIPNUMS (that means FIPNUM boundaries)
    # and horizontal connetions:
    filt_trans_df = trans_df[
        (trans_df["FIPNUM1"] != trans_df["FIPNUM2"]) & (trans_df["DIR"] != "K")
    ]
    unique_pairs = filt_trans_df["FIPNUMPAIR"].unique()
    assert len(unique_pairs) == 3
    assert "5-6" in unique_pairs
    assert "6-5" not in unique_pairs  # because we have sorted them

    assert len(filt_trans_df) < len(trans_df)
    assert set(filt_trans_df["DIR"].unique()) == set(["I", "J"])
    # filt_trans_df.to_csv("fipnumtrans.csv", index=False)


def test_subvectors():
    """Test that we can ask for a few vectors only"""
    eclfiles = EclFiles(DATAFILE)
    init_df = grid.init2df(eclfiles, "PORO")
    assert "PORO" in init_df
    assert "PERMX" not in init_df
    assert "PORV" not in init_df

    init_df = grid.init2df(eclfiles, "P*")
    assert "PORO" in init_df
    assert "PERMX" in init_df
    assert "PVTNUM" in init_df
    assert "SATNUM" not in init_df

    init_df = grid.init2df(eclfiles, ["P*"])
    assert "PORO" in init_df
    assert "PERMX" in init_df
    assert "PVTNUM" in init_df
    assert "SATNUM" not in init_df

    init_df = grid.init2df(eclfiles, ["P*", "*NUM"])
    assert "PORO" in init_df
    assert "PERMX" in init_df
    assert "PVTNUM" in init_df
    assert "SATNUM" in init_df
    assert "MULTZ" not in init_df


def test_dropconstants():
    df = pd.DataFrame(columns=["A", "B"], data=[[1, 1], [2, 1]])
    assert "B" not in grid.dropconstants(df)
    assert "A" in grid.dropconstants(df)
    assert "B" in grid.dropconstants(df, alwayskeep="B")
    assert "B" in grid.dropconstants(df, alwayskeep=["B"])


def test_mergegridframes():
    """Test that we can merge together data for the grid"""
    eclfiles = EclFiles(DATAFILE)
    init_df = grid.init2df(eclfiles)
    grid_geom = grid.gridgeometry2df(eclfiles)

    assert len(init_df) == len(grid_geom)

    merged = grid.merge_gridframes(grid_geom, init_df, pd.DataFrame())
    assert isinstance(merged, pd.DataFrame)
    assert len(merged) == len(grid_geom)

    # Check that PORV is sensible
    assert (
        abs(sum(merged["PORO"] * merged["VOLUME"] - merged["PORV"]))
        / sum(merged["PORV"])
        < 0.00001
    )


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-eclgrid.csv"
    sys.argv = ["eclgrid2csv", DATAFILE, "-o", tmpcsvfile, "--init", "PORO"]
    grid.main()
    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)

    # Do again with also restarts, and using subparsers:
    sys.argv = [
        "ecl2csv",
        "grid",
        DATAFILE,
        "-o",
        tmpcsvfile,
        "--rstdate",
        "first",
        "--init",
        "PORO",
    ]
    ecl2csv.main()
    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)

    # Do again with also restarts:
    sys.argv = [
        "eclgrid2csv",
        DATAFILE,
        "-o",
        tmpcsvfile,
        "--rstdate",
        "2001-02-01",
        "--init",
        "PORO",
    ]
    grid.main()
    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)

    # Test with constants dropping
    sys.argv = ["eclgrid2csv", DATAFILE, "-o", tmpcsvfile, "--dropconstants"]
    grid.main()
    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    # That PVTNUM is constant is a particular feature
    # of the test dataset.
    assert "PVTNUM" not in disk_df
    assert not disk_df.empty
    os.remove(tmpcsvfile)


def test_rstdates():
    eclfiles = EclFiles(DATAFILE)
    # rstfile = eclfiles.get_rstfile()

    alldates = grid.rstdates(eclfiles)
    assert len(alldates) == 4

    didx = grid.dates2rstindices(eclfiles, "all")
    assert len(didx[0]) == len(alldates)
    assert len(didx[1]) == len(alldates)
    assert isinstance(didx[0][0], int)
    assert isinstance(didx[1][0], datetime.date)
    assert didx[1][0] == alldates[0]
    assert didx[1][-1] == alldates[-1]

    first = grid.dates2rstindices(eclfiles, "first")
    assert first[1][0] == alldates[0]

    last = grid.dates2rstindices(eclfiles, "last")
    assert last[1][0] == alldates[-1]

    dates = grid.rstdates(eclfiles)
    assert isinstance(dates, list)

    # Test with missing RST file:
    eclfiles = EclFiles("BOGUS.DATA")
    with pytest.raises(IOError):
        eclfiles.get_rstfile()


def test_rst2df():
    eclfiles = EclFiles(DATAFILE)
    assert grid.rst2df(eclfiles, "first").shape == (35817, 23)
    assert grid.rst2df(eclfiles, "last").shape == (35817, 23)
    assert grid.rst2df(eclfiles, "all").shape == (35817, 23 * 4)

    assert "SOIL" in grid.rst2df(eclfiles, date="first", dateinheaders=False)
    assert (
        "SOIL@2000-01-01" in grid.rst2df(eclfiles, "first", dateinheaders=True).columns
    )

    rst_df = grid.rst2df(eclfiles, "first", datestacked=True)
    assert "DATE" in rst_df
    assert rst_df["DATE"].unique()[0] == "2000-01-01"
    rst_df = grid.rst2df(eclfiles, "all", datestacked=True)
    assert len(rst_df["DATE"].unique()) == len(grid.rstdates(eclfiles))
    assert rst_df.shape == (4 * 35817, 23 + 1)  # "DATE" is now the extra column

    # Check vector slicing:
    rst_df = grid.rst2df(eclfiles, "first", vectors="S???")
    assert rst_df.shape == (35817, 3)
    assert "SGAS" in rst_df
    assert "SWAT" in rst_df
    assert "SOIL" in rst_df  # This is actually computed
    assert "FIPWAT" not in rst_df

    # Test more vectors:
    rst_df = grid.rst2df(eclfiles, "first", vectors=["PRESSURE", "SWAT"])
    assert "PRESSURE" in rst_df
    assert "SWAT" in rst_df
    assert "SGAS" not in rst_df
    assert "SOIL" not in rst_df

    # Check that we can avoid getting SOIL if we are explicit:
    rst_df = grid.rst2df(eclfiles, "first", vectors=["SGAS", "SWAT"])
    assert "SOIL" not in rst_df
    assert "SGAS" in rst_df
    assert "SWAT" in rst_df
