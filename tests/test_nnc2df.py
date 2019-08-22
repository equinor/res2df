# -*- coding: utf-8 -*-
"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd

from ecl2df import nnc2df, faults2df, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


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


def test_nnc2df_faultnames():
    """Add faultnames from FAULTS keyword to connections"""
    eclfiles = EclFiles(DATAFILE)
    nncdf = nnc2df.nnc2df(eclfiles)
    faultsdf = faults2df.deck2df(eclfiles.get_ecldeck())

    merged = pd.merge(
        nncdf,
        faultsdf,
        how="left",
        left_on=["I1", "J1", "K1"],
        right_on=["I", "J", "K"],
    )
    merged = pd.merge(
        merged,
        faultsdf,
        how="left",
        left_on=["I2", "J2", "K2"],
        right_on=["I", "J", "K"],
    )
    # Fix columnnames so that we don't get FACE_x and FACE_y etc.
    # Remove I_x, J_x, K_x (and _y) which is not needed


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-nnc.csv"
    sys.argv = ["ecl2csv", "nnc", DATAFILE, "-o", tmpcsvfile]
    ecl2csv.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    assert "I1" in disk_df
    assert "TRAN" in disk_df
    os.remove(tmpcsvfile)
