# -*- coding: utf-8 -*-
"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd
import numpy as np
import logging

from ecl2df import rft2df, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")

logger = logging.getLogger("")
logger.setLevel(logging.DEBUG)


def test_rftrecords2df():
    eclfiles = EclFiles(DATAFILE)

    rftrecs = rft2df._rftrecords2df(eclfiles)
    assert len(rftrecs[rftrecs["recordname"] == "TIME"]) == len(
        rftrecs["timeindex"].unique()
    )
    assert set(rftrecs["recordtype"].unique()) == set(["REAL", "INTE", "CHAR"])
    assert rftrecs["timeindex"].dtype == np.int


def test_rft2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    rftdf = rft2df.rft2df(eclfiles)

    assert not rftdf.empty
    assert len(rftdf.columns)


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-rft.csv"
    sys.argv = ["rft2csv", DATAFILE, "-o", tmpcsvfile]
    rft2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)


def test_main_subparsers():
    """Test command line interface"""
    tmpcsvfile = ".TMP-rft.csv"
    sys.argv = ["ecl2csv", "rft", DATAFILE, "-o", tmpcsvfile]
    ecl2csv.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)
