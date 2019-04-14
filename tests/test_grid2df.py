#_ -*- coding: utf-8 -*-
"""Test module for grid2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import pytest

import pandas as pd

from ecl.eclfile import EclFile
from ecl.grid import EclGrid

from ecl2df import grid2df

DATAFILE = "data/reek/eclipse/model/2_R001_REEK-0.DATA"


def test_data2eclfiles():
    """Test that we can make EclGrid/Init objects from files"""
    result = grid2df.data2eclfiles(DATAFILE)

    assert isinstance(result, tuple)
    assert isinstance(result[0], EclFile)
    assert isinstance(result[1], EclGrid)
    assert isinstance(result[2], EclFile)

    with pytest.raises(IOError):
        result = grid2df.data2eclfiles("NOT-EXISTING-FILE")


def test_gridgeometry2df():
    """Test that dataframes are produced"""
    eclfiles = grid2df.data2eclfiles(DATAFILE)
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
    eclfiles = grid2df.data2eclfiles(DATAFILE)
    init_df = grid2df.init2df(eclfiles[2], eclfiles[1].getNumActive())

    assert isinstance(init_df, pd.DataFrame)
    assert not init_df.empty
    assert "PERMX" in init_df
    assert "PORO" in init_df


def test_mergegridframes():
    """Test that we can merge together data for the grid"""
    eclfiles = grid2df.data2eclfiles(DATAFILE)
    init_df = grid2df.init2df(eclfiles[2], eclfiles[1].getNumActive())
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
    eclfiles = grid2df.data2eclfiles(DATAFILE)
    rstfile = eclfiles[3]
    rstfilename = eclfiles[4]
    assert rstfile

    # assert isinstance(rstfile, EclFile)
    dates = grid2df.rstdates(rstfile, rstfilename)
    assert isinstance(dates, list)
    print(dates)
