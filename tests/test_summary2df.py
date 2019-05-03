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

from ecl2df import summary2df
from ecl2df.eclfiles import EclFiles

DATAFILE = "data/reek/eclipse/model/2_R001_REEK-0.DATA"


def test_summary2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    sumdf = summary2df.get_smry(eclfiles)

    assert not sumdf.empty
    assert sumdf.index.name == "DATE"
    assert len(sumdf.columns)
    assert "FOPT" in sumdf.columns


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-sum.csv"
    sys.argv = ["summary2df", DATAFILE, "-o", tmpcsvfile]
    summary2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    assert "FOPT" in disk_df
    os.remove(tmpcsvfile)
