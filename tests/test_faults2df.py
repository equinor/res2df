# -*- coding: utf-8 -*-
"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd

from ecl2df import faults2df, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_faults2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    faultsdf = faults2df.deck2df(eclfiles.get_ecldeck())

    assert "NAME" in faultsdf
    assert "I" in faultsdf
    assert "J" in faultsdf
    assert "K" in faultsdf
    assert "FACE" in faultsdf

    assert not faultsdf.empty


def test_str2df():
    deckstr = """
FAULTS
  'A' 1 2 3 4 5 6 'I' /
  'B' 2 3 4 5 6 7 'J' /
/
"""
    deck = EclFiles.str2deck(deckstr)
    faultsdf = faults2df.deck2df(deck)

    assert len(faultsdf) == 16


def test_multiplestr2df():
    deckstr = """
FAULTS
  'A' 1 2 3 4 5 6 'I' /
  'B' 2 3 4 5 6 7 'J' /
/
FAULTS
  'C' 1 1 3 3 10 15 'I' /
  'D' 2 2 4 4 10 10 'J' /
/
"""
    deck = EclFiles.str2deck(deckstr)
    faultsdf = faults2df.deck2df(deck).set_index("NAME")

    assert len(faultsdf) == 23
    assert len(faultsdf.loc[["D"]]) == 1  # Pass lists to .loc for single row
    assert len(faultsdf.loc["C"]) == 6


def test_main_subparser():
    """Test command line interface with subparsers"""
    tmpcsvfile = ".TMP-faultsdf.csv"
    sys.argv = ["ecl2csv", "faults", DATAFILE, "-o", tmpcsvfile]
    ecl2csv.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-faultsdf.csv"
    sys.argv = ["faults2csv", DATAFILE, "-o", tmpcsvfile]
    faults2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)
