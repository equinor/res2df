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

from ecl2df import faults2df
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_faults2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    faultsdf = faults2df.deck2faultsdf(eclfiles.get_ecldeck())

    assert "NAME" in faultsdf
    assert "IX1" in faultsdf
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
    faultsdf = faults2df.deck2faultsdf(deck)
    assert len(faultsdf) == 2


def test_multiplestr2df():
    deckstr = """
FAULTS
  'A' 1 2 3 4 5 6 'I' /
  'B' 2 3 4 5 6 7 'J' /
/
FAULTS
  'C' 1 2 3 40 50 60 'I' /
  'D' 2 3 4 50 60 70 'J' /
/
"""
    deck = EclFiles.str2deck(deckstr)
    faultsdf = faults2df.deck2faultsdf(deck)
    assert len(faultsdf) == 4
    assert len(faultsdf["NAME"].unique()) == 4


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-gruptree.csv"
    sys.argv = ["faults2csv", DATAFILE, "-o", tmpcsvfile]
    faults2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)
