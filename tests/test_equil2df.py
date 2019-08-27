# -*- coding: utf-8 -*-
"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pytest

import pandas as pd

from ecl2df import equil2df, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_equil2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    equildf = equil2df.deck2df(eclfiles.get_ecldeck())

    assert not equildf.empty


def test_decks():
    """Test some string decks"""
    deckstr = """
OIL
WATER
GAS

EQUIL
 2000 200 2200 /
"""
    deck = EclFiles.str2deck(deckstr)
    df = equil2df.deck2df(deck)
    assert df["OWC"].values == 2200
    assert len(df) == 1
    assert "IGNORE1" not in df

    deckstr = """
OIL
WATER

EQUIL
 2000 200 2200 /
"""
    deck = EclFiles.str2deck(deckstr)
    df = equil2df.deck2df(deck)
    assert df["OWC"].values == 2200
    assert len(df) == 1
    assert "IGNORE1" not in df

    deckstr = """
GAS
WATER

EQUIL
 2000 200 2200 /
"""
    deck = EclFiles.str2deck(deckstr)
    df = equil2df.deck2df(deck)
    assert df["GWC"].values == 2200
    assert "OWC" not in df
    assert len(df) == 1
    assert "IGNORE2" not in df

    deckstr = """
GAS
OIL

EQUIL
 2000 200 2200 1 2100 3 /
"""
    deck = EclFiles.str2deck(deckstr)
    df = equil2df.deck2df(deck)
    assert df["GOC"].values == 2100
    assert "GWC" not in df
    assert "OWC" not in df
    assert len(df) == 1
    assert "IGNORE2" not in df


def test_ntequl():
    """Test that we can infer NTEQUL when not supplied"""
    deckstr = """
GAS
OIL

EQUIL
 2000 200 2200 1 2100 3 /
 3000 200 2200 1 2100 3 /
"""
    df = equil2df.deck2df(deckstr)
    assert set(df["GOC"].values) == set([2100, 2100])
    assert len(df) == 2

    # Supply correct NTEQUL instead of estimating
    df = equil2df.deck2df(deckstr, 2)
    assert len(df) == 2

    # Supplying wrong NTEQUIL:
    df = equil2df.deck2df(deckstr, 1)
    # We are not able to catch this situation..
    assert len(df) == 1
    # But this will fail:
    with pytest.raises(ValueError):
        equil2df.deck2df(deckstr, 3)

    deckstr = """
GAS
OIL

EQLDIMS
 2 /

EQUIL
 2000 200 2200 1 2100 3 /
 3000 200 2200 1 2100 3 /
"""
    df = equil2df.deck2df(deckstr)
    assert set(df["GOC"].values) == set([2100, 2100])
    assert len(df) == 2


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-equil.csv"
    sys.argv = ["equil2csv", DATAFILE, "-o", tmpcsvfile]
    equil2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)


def test_main_subparser():
    """Test command line interface"""
    tmpcsvfile = ".TMP-equil.csv"
    sys.argv = ["ecl2csv", "equil", DATAFILE, "-o", tmpcsvfile]
    ecl2csv.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)
