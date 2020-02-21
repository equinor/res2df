# -*- coding: utf-8 -*-
"""Test module for wcon"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd

from ecl2df import wcon, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_wcon2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    wcondf = wcon.deck2df(eclfiles.get_ecldeck())

    assert not wcondf.empty
    assert "DATE" in wcondf  # for all data
    assert "KEYWORD" in wcondf
    for col in wcondf.columns:
        assert col == col.upper()


def test_str2df():
    wconstr = """
WCONHIST
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wcondf = wcon.deck2df(deck)
    assert len(wcondf) == 1

    wconstr = """
WCONINJH
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wcondf = wcon.deck2df(deck)
    assert len(wcondf) == 1

    wconstr = """
WCONINJE
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wcondf = wcon.deck2df(deck)
    assert len(wcondf) == 1

    wconstr = """
WCONPROD
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wcondf = wcon.deck2df(deck)
    assert len(wcondf) == 1


def test_tstep():
    schstr = """
DATES
   1 MAY 2001 /
/

WCONHIST
 'OP1' 1000  /
/

TSTEP
  1 /

WCONHIST
 'OP1' 2000 /
/

TSTEP
  2 3 /

WCONHIST
  'OP1' 3000 /
/
"""
    deck = EclFiles.str2deck(schstr)
    wcondf = wcon.deck2df(deck)
    dates = [str(x) for x in wcondf["DATE"].unique()]
    assert len(dates) == 3
    assert "2001-05-01" in dates
    assert "2001-05-02" in dates
    assert "2001-05-07" in dates


def test_main(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-wcondf.csv")
    sys.argv = ["wcon2csv", DATAFILE, "-o", str(tmpcsvfile)]
    wcon.main()

    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty


def test_main_subparsers(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-wcondf.csv")
    sys.argv = ["ecl2csv", "wcon", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()

    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
