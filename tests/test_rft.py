# -*- coding: utf-8 -*-
"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd
import numpy as np

from ecl2df import rft, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_rftrecords2df():
    eclfiles = EclFiles(DATAFILE)

    rftrecs = rft._rftrecords2df(eclfiles)
    assert len(rftrecs[rftrecs["recordname"] == "TIME"]) == len(
        rftrecs["timeindex"].unique()
    )
    assert set(rftrecs["recordtype"].unique()) == set(["REAL", "INTE", "CHAR"])
    assert rftrecs["timeindex"].dtype == np.int


def test_rft2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    rftdf = rft.rft2df(eclfiles)
    assert "ZONE" in rftdf
    assert not rftdf.empty
    assert len(rftdf.columns)


def test_main(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-rft.csv")
    sys.argv = ["rft2csv", DATAFILE, "-o", str(tmpcsvfile)]
    rft.main()

    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty


def test_main_subparsers(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-rft.csv")
    sys.argv = ["ecl2csv", "rft", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()

    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty

    tmpcsvfile = tmpdir.join(".TMP-rft2.csv")
    # Test with RFT file as argument:
    sys.argv = [
        "ecl2cvsv",
        "rft",
        "-v",
        DATAFILE.replace(".DATA", ".RFT"),
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()
    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
