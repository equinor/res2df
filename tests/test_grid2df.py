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


def test_mergegridframes():
    """Test that we can merge together data for the grid"""
    eclfiles = EclFiles(DATAFILE)
    init_df = grid2df.init2df(
        eclfiles.get_initfile(), eclfiles.get_egrid().getNumActive()
    )
    grid_geom = grid2df.gridgeometry2df(eclfiles)

    assert len(init_df) == len(grid_geom)

    merged = grid2df.merge_gridframes(grid_geom, init_df)
    assert isinstance(merged, pd.DataFrame)
    assert len(merged) == len(grid_geom)


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-eclgrid.csv"
    sys.argv = ["eclgrid2csv", DATAFILE, "-o", tmpcsvfile]
    grid2df.main()
    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)


def test_rstdates():
    eclfiles = EclFiles(DATAFILE)
    rstfile = eclfiles.get_rstfile()
    assert rstfile

    dates = grid2df.rstdates(eclfiles)
    print(dates)
    assert isinstance(dates, list)


def test_rst2df():
    eclfiles = EclFiles(DATAFILE)
    print(grid2df.rst2df(eclfiles, "first").head())
    print(grid2df.rst2df(eclfiles, "all").head())
    grid2df.rst2df(eclfiles, "last")
    grid2df.rst2df(eclfiles, datetime.date(2000, 1, 1))
    grid2df.rst2df(eclfiles, "2000-01-01")
