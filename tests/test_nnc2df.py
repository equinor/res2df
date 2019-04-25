# -*- coding: utf-8 -*-
"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import pytest

import pandas as pd

from ecl.eclfile import EclFile
from ecl.grid import EclGrid

from ecl2df import nnc2df
from ecl2df.eclfiles import EclFiles

DATAFILE = "data/reek/eclipse/model/2_R001_REEK-0.DATA"


def test_nnc2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    nncdf = nnc2df.nnc2df(eclfiles)

    assert not nncdf.empty
    assert "I1" in nncdf
    assert "J1" in nncdf
    assert "K1" in nncdf
    assert "I2" in nncdf
    assert "J2" in nncdf
    assert "K2" in nncdf
    assert "TRAN" in nncdf


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-nnc.csv"
    sys.argv = ["nnc2df", DATAFILE, "-o", tmpcsvfile]
    nnc2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    assert "I1" in disk_df
    assert "TRAN" in disk_df
    os.remove(tmpcsvfile)
