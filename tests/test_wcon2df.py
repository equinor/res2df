# -*- coding: utf-8 -*-
"""Test module for wcon2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd

from ecl2df import wcon2df
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_wcon2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    wcondf = wcon2df.deck2wcondf(eclfiles.get_ecldeck())

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
    wcondf = wcon2df.deck2wcondf(deck)
    assert len(wcondf) == 1

    wconstr = """
WCONINJH
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wcondf = wcon2df.deck2wcondf(deck)
    assert len(wcondf) == 1

    wconstr = """
WCONINJE
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wcondf = wcon2df.deck2wcondf(deck)
    assert len(wcondf) == 1

    wconstr = """
WCONPROD
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wcondf = wcon2df.deck2wcondf(deck)
    assert len(wcondf) == 1




def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-wcondf.csv"
    sys.argv = ["wcon2csv", DATAFILE, "-o", tmpcsvfile]
    wcon2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    #os.remove(tmpcsvfile)
