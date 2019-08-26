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
-- RUNSPEC -- (this line is optional)

TABDIMS
  2 /

-- PROPS -- (optional)

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
    assert "SATNUM" in satdf
    assert len(satdf2["SATNUM"].unique()) == 2
    assert len(satdf2) == 5

    # Try empty/bogus data:
    bogusdf = satfunc2df.deck2df("SWRF\n 0 /\n")
    # (warnings should be issued)
    assert bogusdf.empty


def test_sgof_satnuminferrer():
    sgofstr = """
SGOF
  0 0 1 1
  1 1 0 0
/
  0 0 1 1
  0.5 0.5 0.5 0.5
  1 1 0 0
/
  0 0 1 0
  0.1 0.1 0.1 0.1
  1 1 0 0
/
"""
    assert satfunc2df.guess_satnumcount(sgofstr) == 3
    sgofdf = satfunc2df.deck2df(sgofstr)
    assert "SATNUM" in sgofdf
    assert len(sgofdf["SATNUM"].unique()) == 3
    assert len(sgofdf) == 8

    # This illustrates how we cannot do it, CRITICAL
    # logging errors will be displayed:
    sgofdf = satfunc2df.deck2df(EclFiles.str2deck(sgofstr))
    assert len(sgofdf["SATNUM"].unique()) == 1

    # Write to file and try to parse it with command line:
    sgoffile = "__sgof_tmp.txt"
    with open(sgoffile, "w") as sgof_f:
        sgof_f.write(sgofstr)

    sys.argv = ["ecl2csv", "satfunc", sgoffile, "-o", sgoffile + ".csv"]
    ecl2csv.main()
    parsed_sgof = pd.read_csv(sgoffile + ".csv")
    assert len(parsed_sgof["SATNUM"].unique()) == 3


def test_injectsatnumcount():
    """Test that we always get out a string with TABDIMS"""
    assert "TABDIMS" in satfunc2df.inject_satnumcount("", 0)
    assert "TABDIMS" in satfunc2df.inject_satnumcount("", 1)
    assert "TABDIMS" in satfunc2df.inject_satnumcount("TABDIMS", 1)
    assert "99" in satfunc2df.inject_satnumcount("", 99)


def test_guess_satnumcount():
    # We always require a newline after a "/" in the Eclipse syntax
    # (anything between a / and \n is ignored)
    assert satfunc2df.guess_satnumcount("SWOF\n0/\n0/\n") == 2
    assert satfunc2df.guess_satnumcount("SWOF\n0/\n0/ \n0/\n") == 3
    assert satfunc2df.guess_satnumcount("SWFN\n0/\n\n0/\n") == 2
    assert satfunc2df.guess_satnumcount("SGOF\n0/\n") == 1
    assert satfunc2df.guess_satnumcount("SGOF\n0/\n0/\n") == 2
    assert satfunc2df.guess_satnumcount("SGOF\n0/\n0/\n0/\n") == 3
    assert satfunc2df.guess_satnumcount("SGOF\n0 0 0 0/\n0 0 0 0/\n0 0 0 0/\n") == 3
    assert (
        satfunc2df.guess_satnumcount(
            "SGOF\n0 0 0 0 1 1 1 1/\n0 0 0 0 1 1 1 1/\n0 0 0 0 1 1 1/\n"
        )
        == 3
    )


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