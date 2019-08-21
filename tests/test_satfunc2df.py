# -*- coding: utf-8 -*-
"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd

from ecl2df import satfunc2df, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_satfunc2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    satdf = satfunc2df.deck2df(eclfiles.get_ecldeck())

    assert not satdf.empty
    assert "KEYWORD" in satdf  # for all data
    assert "SATNUM" in satdf  # for all data

    assert "SWOF" in satdf["KEYWORD"].unique()
    assert "SGOF" in satdf["KEYWORD"].unique()
    assert "SW" in satdf
    assert "KRW" in satdf
    assert "KROW" in satdf
    assert "SG" in satdf
    assert "KROG" in satdf
    assert satdf["SATNUM"].unique() == [1]


def test_str2df():
    swofstr = """
SWOF
 0 0 1 1
 1 1 0 0
 /
"""
    deck = EclFiles.str2deck(swofstr)
    satdf = satfunc2df.deck2df(deck)
    assert len(satdf) == 2


    swofstr2 = """
SWOF
 0 0 1 1
 1 1 0 0
/
 0 0 1 1
 0.5 0.5 0.5 0.5
 1 1 0 0
/
"""
    deck2 = EclFiles.str2deck(swofstr2)
    satdf2 = satfunc2df.deck2df(deck2)
    print(satdf2)
    assert 'SATNUM' in satdf
    assert len(satdf['SATNUM'].unique()) == 2
    assert len(satdf) == 2


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-satfunc.csv"
    sys.argv = ["satfunc2csv", DATAFILE, "-o", tmpcsvfile]
    satfunc2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)


def test_main_subparsers():
    """Test command line interface"""
    tmpcsvfile = ".TMP-satfunc.csv"
    sys.argv = ["ecl2csv", "satfunc", DATAFILE, "-o", tmpcsvfile]
    ecl2csv.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)
