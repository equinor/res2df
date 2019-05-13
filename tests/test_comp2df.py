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

from ecl2df import compdat2df
from ecl2df.eclfiles import EclFiles

DATAFILE = "data/reek/eclipse/model/2_R001_REEK-0.DATA"


def test_comp2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    compdfs = compdat2df.deck2compdatsegsdfs(eclfiles)

    assert not compdfs[0].empty
    assert compdfs[1].empty  # REEK demo does not include multisegment wells
    assert compdfs[2].empty
    assert len(compdfs[0].columns)


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-compdat.csv"
    sys.argv = ["compdat2csv", DATAFILE, "-o", tmpcsvfile]
    compdat2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)
