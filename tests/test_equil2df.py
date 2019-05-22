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

from ecl2df import equil2df
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR,
                        "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_equil2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    equildf = equil2df.deck2equildf(eclfiles.get_ecldeck())

    assert not equildf.empty


def test_deck1():
    deckstr = """
OIL
WATER
GAS

EQUIL
 2000 200 2200 /
"""
    deck = EclFiles.str2deck(deckstr)
    df = equil2df.deck2equildf(deck)
    assert df['OWC'].values == 2200


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-equil.csv"
    sys.argv = ["equil2csv", DATAFILE, "-o", tmpcsvfile]
    equil2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)
