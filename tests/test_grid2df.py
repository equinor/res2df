# -*- coding: utf-8 -*-
"""Test module for grid2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import datetime
import pandas as pd

import pytest

from ecl.eclfile import EclFile
from ecl.grid import EclGrid

from ecl2df import grid2df
from ecl2df.eclfiles import EclFiles

DATAFILE = "data/reek/eclipse/model/2_R001_REEK-0.DATA"


def test_gridgeometry2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    grid_geom = grid2df.gridgeometry2df(eclfiles)

    assert isinstance(grid_geom, pd.DataFrame)
    assert not grid_geom.empty

    assert "I" in grid_geom
    assert "J" in grid_geom
    assert "K" in grid_geom
    assert "X" in grid_geom
    assert "Y" in grid_geom
    assert "Z" in grid_geom
    assert "VOLUME" in grid_geom


def test_init2df():
    """Test that dataframe with INIT vectors can be produced"""
    eclfiles = EclFiles(DATAFILE)
    init_df = grid2df.init2df(
        eclfiles.get_initfile(), eclfiles.get_egrid().getNumActive()
    )

    assert isinstance(init_df, pd.DataFrame)
    assert not init_df.empty
    assert "PERMX" in init_df
    assert "PORO" in init_df


def test_subvectors():
    """Test that we can ask for a few vectors only"""
    eclfiles = EclFiles(DATAFILE)
    init_df = grid2df.init2df(
        eclfiles.get_initfile(), eclfiles.get_egrid().getNumActive(), "PORO"
    )
    assert "PORO" in init_df
    assert "PERMX" not in init_df

    init_df = grid2df.init2df(
        eclfiles.get_initfile(), eclfiles.get_egrid().getNumActive(), "P*"
    )
    assert "PORO" in init_df
    assert "PERMX" in init_df
    assert "PVTNUM" in init_df
    assert "SATNUM" not in init_df

    init_df = grid2df.init2df(
        eclfiles.get_initfile(), eclfiles.get_egrid().getNumActive(), ["P*"]
    )
    assert "PORO" in init_df
    assert "PERMX" in init_df
    assert "PVTNUM" in init_df
    assert "SATNUM" not in init_df

    init_df = grid2df.init2df(
        eclfiles.get_initfile(), eclfiles.get_egrid().getNumActive(), ["P*", "*NUM"]
    )
    assert "PORO" in init_df
    assert "PERMX" in init_df
    assert "PVTNUM" in init_df
    assert "SATNUM" in init_df
    assert "MULTZ" not in init_df


def test_mergegridframes():
    """Test that we can merge together data for the grid"""
    eclfiles = EclFiles(DATAFILE)
    init_df = grid2df.init2df(
        eclfiles.get_initfile(), eclfiles.get_egrid().getNumActive()
    )
    grid_geom = grid2df.gridgeometry2df(eclfiles)

    assert len(init_df) == len(grid_geom)

    merged = grid2df.merge_gridframes(grid_geom, init_df, pd.DataFrame())
    assert isinstance(merged, pd.DataFrame)
    assert len(merged) == len(grid_geom)


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-eclgrid.csv"
    sys.argv = ["eclgrid2csv", DATAFILE, "-o", tmpcsvfile, "--init", "PORO"]
    grid2df.main()
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
        "first",
        "--init",
        "PORO",
    ]
    grid2df.main()
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
    grid2df.main()
    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)


def test_rstdates():
    eclfiles = EclFiles(DATAFILE)
    rstfile = eclfiles.get_rstfile()

    alldates = grid2df.rstdates(eclfiles)
    assert len(alldates) == 4

    didx = grid2df.dates2rstindices(eclfiles, "all")
    assert len(didx[0]) == len(alldates)
    assert len(didx[1]) == len(alldates)
    assert isinstance(didx[0][0], int)
    assert isinstance(didx[1][0], datetime.date)
    assert didx[1][0] == alldates[0]
    assert didx[1][-1] == alldates[-1]

    first = grid2df.dates2rstindices(eclfiles, "first")
    assert first[1][0] == alldates[0]

    last = grid2df.dates2rstindices(eclfiles, "last")
    assert last[1][0] == alldates[-1]

    dates = grid2df.rstdates(eclfiles)
    assert isinstance(dates, list)


def test_rst2df():
    eclfiles = EclFiles(DATAFILE)
    assert grid2df.rst2df(eclfiles, "first").shape == (35817, 22)
    assert grid2df.rst2df(eclfiles, "last").shape == (35817, 22)
    assert grid2df.rst2df(eclfiles, "all").shape == (35817, 22 * 4)
