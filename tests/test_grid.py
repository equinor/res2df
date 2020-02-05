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
    assert "ZONE" in grid_geom


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


def test_df():
    """Test the df function"""
    eclfiles = EclFiles(DATAFILE)
    # assert error..
    with pytest.raises(TypeError):
        grid.df()

    grid_df = grid.df(eclfiles)
    assert not grid_df.empty
    assert "I" in grid_df  # From GRID
    assert "PORO" in grid_df  # From INIT
    assert "SOIL" not in grid_df  # We do not get RST unless we ask for it.

    grid_df = grid.df(eclfiles, vectors="*")
    assert "I" in grid_df  # From GRID
    assert "PORO" in grid_df  # From INIT
    assert "SOIL" not in grid_df  # We do not get RST unless we ask for it.

    grid_df = grid.df(eclfiles, vectors=["*"])
    assert "I" in grid_df  # From GRID
    assert "PORO" in grid_df  # From INIT
    assert "SOIL" not in grid_df  # We do not get RST unless we ask for it.

    grid_df = grid.df(eclfiles, vectors="PRESSURE")
    assert "I" in grid_df
    assert "PRESSURE" not in grid_df  # that vector is only in RST
    assert len(grid_df) == 35817
    assert "VOLUME" in grid_df

    grid_df = grid.df(eclfiles, vectors=["PRESSURE"])
    assert "I" in grid_df
    assert not grid_df.empty
    assert "PRESSURE" not in grid_df
    geometry_cols = len(grid_df.columns)

    grid_df = grid.df(eclfiles, vectors=["PRESSURE"], rstdates="last", stackdates=True)
    assert "PRESSURE" in grid_df
    assert len(grid_df.columns) == geometry_cols + 2
    assert "DATE" in grid_df  # awaits stacking

    grid_df = grid.df(eclfiles, vectors="PRESSURE", rstdates="last")
    assert "PRESSURE" in grid_df
    assert len(grid_df.columns) == geometry_cols + 1

    grid_df = grid.df(eclfiles, vectors="PRESSURE", rstdates="last", dateinheaders=True)
    assert "PRESSURE" not in grid_df
    assert "PRESSURE@2001-08-01" in grid_df

    grid_df = grid.df(eclfiles, vectors="PRESSURE", rstdates="all", stackdates=True)
    assert "PRESSURE" in grid_df
    assert len(grid_df.columns) == geometry_cols + 2
    assert "DATE" in grid_df
    assert len(grid_df["DATE"].unique()) == 4

    grid_df = grid.df(eclfiles, vectors="PORO")
    assert "I" in grid_df
    assert "PORO" in grid_df
    assert len(grid_df) == 35817
    assert "DATE" not in grid_df

    grid_df = grid.df(eclfiles, vectors="PORO", rstdates="all")
    assert "I" in grid_df
    assert "PORO" in grid_df
    assert "DATE" not in grid_df
    # (no RST columns, so no DATE info in the daaframe)
    # (warnings should be printed)

    grid_df = grid.df(eclfiles, vectors="PORO", rstdates="all", stackdates=True)
    assert "I" in grid_df
    assert "PORO" in grid_df
    assert "DATE" not in grid_df
    # DATE is not included as it really does not make sense. The code
    # could have multiplied up the static dataframe each tagged with a date
    # but not for now.


def test_main(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-eclgrid.csv")
    sys.argv = ["eclgrid2csv", "-v", DATAFILE, "-o", str(tmpcsvfile), "--init", "PORO"]
    grid.main()
    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
    os.remove(str(tmpcsvfile))

    # Do again with also restarts, and using subparsers:
    sys.argv = [
        "ecl2csv",
        "grid",
        DATAFILE,
        "-o",
        str(tmpcsvfile),
        "--rstdate",
        "first",
        "--init",
        "PORO",
    ]
    ecl2csv.main()
    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
    os.remove(str(tmpcsvfile))

    # Do again with also restarts:
    sys.argv = [
        "eclgrid2csv",
        DATAFILE,
        "-o",
        str(tmpcsvfile),
        "--rstdate",
        "2001-02-01",
        "--init",
        "PORO",
    ]
    grid.main()
    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
    os.remove(str(tmpcsvfile))

    # Test with constants dropping
    sys.argv = ["eclgrid2csv", DATAFILE, "-o", str(tmpcsvfile), "--dropconstants"]
    grid.main()
    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    # That PVTNUM is constant is a particular feature
    # of the test dataset.
    assert "PVTNUM" not in disk_df
    assert not disk_df.empty


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

    rst_df = grid.rst2df(eclfiles, "first", stackdates=True)
    assert "DATE" in rst_df
    assert rst_df["DATE"].unique()[0] == "2000-01-01"
    rst_df = grid.rst2df(eclfiles, "all", stackdates=True)
    assert len(rst_df["DATE"].unique()) == len(grid.rstdates(eclfiles))
    assert rst_df.shape == (4 * 35817, 23 + 1)  # "DATE" is now the extra column

    # Check vector slicing:
    rst_df = grid.rst2df(eclfiles, "first", vectors="S???")
    assert rst_df.shape == (35817, 3)
    assert "SGAS" in rst_df
    assert "SWAT" in rst_df
    assert "SOIL" in rst_df  # This is actually computed
    assert "FIPWAT" not in rst_df

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
