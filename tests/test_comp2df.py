# -*- coding: utf-8 -*- """Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd

from ecl2df import compdat2df
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")

SCHFILE = os.path.join(TESTDIR, "./data/reek/eclipse/include/schedule/reek_history.sch")


def test_comp2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    compdfs = compdat2df.deck2compdatsegsdfs(eclfiles.get_ecldeck())

    assert not compdfs["COMPDAT"].empty
    assert compdfs["WELSEGS"].empty  # REEK demo does not include multisegment wells
    assert compdfs["COMPSEGS"].empty
    assert len(compdfs["COMPDAT"].columns)


def test_schfile2df():
    """Test that we can process individual files"""
    deck = EclFiles.file2deck(SCHFILE)
    compdfs = compdat2df.deck2compdatsegsdfs(deck)
    assert len(compdfs["COMPDAT"].columns)
    assert not compdfs["COMPDAT"].empty


def test_str2df():
    schstr = """
WELSPECS
 'OP1' 'OPWEST' 41 125 1759.74 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
/

COMPDAT
 'OP1' 33 110 31 31 'OPEN' 0 6467.31299 0.216 506642.25  0.0 0.0 'Y' 7.18 /
-- comments.
/

WELSEGS
  'OP1' 1689 1923 1.0E-5 'ABS' 'HFA' 'HO' / comment without -- identifier
-- foo bar
   2 2 1 1 1923.9 1689.000 0.1172 0.000015  /
/

COMPSEGS
  'OP1' / -- Yet a comment
  -- comment
  41 125 29  5 2577.0 2616.298 / icd on branch 1 in segment 17
/
-- (WSEGVALS is not processed)
WSEGVALV
  'OP1'   166   1   7.4294683E-06  0 / icd on segment 17, cell 41 125 29
/
"""
    deck = EclFiles.str2deck(schstr)
    compdfs = compdat2df.deck2compdatsegsdfs(deck)
    compdat = compdfs["COMPDAT"]
    welsegs = compdfs["WELSEGS"]
    compsegs = compdfs["COMPSEGS"]
    assert "WELL" in compdat
    assert len(compdat) == 1
    assert compdat["WELL"].unique()[0] == "OP1"

    # Check that we have not used the very long sunbeam term here:
    assert "CONNECTION_TRANSMISSIBILITY_FACTOR" not in compdat
    assert "TRAN" in compdat

    assert "Kh" not in compdat  # Mixed-case should not be used.
    assert "KH" in compdat

    # Make sure the ' are ignored:
    assert compdat["OP/SH"].unique()[0] == "OPEN"

    # Continue to WELSEGS
    assert len(welsegs) == 1  # First record is appended to every row.

    # Since we have 'ABS' in WELSEGS, there should be an extra column called 'SEGMENT_MD'
    assert "SEGMENT_MD" in welsegs
    assert welsegs["SEGMENT_MD"].max() == 1923.9

    # Test COMPSEGS
    assert len(compsegs) == 1
    assert "WELL" in compsegs
    assert compsegs["WELL"].unique()[0] == "OP1"
    assert len(compsegs.iloc[0]) == 9

def test_unrollcompdatk1k2():
    schstr = """
COMPDAT
  -- K1 to K2 is a range of 11 layers, should be automatically
  -- unrolled to 11 rows.
  'OP1' 33 44 10 20  /
/
"""
    df = compdat2df.deck2compdatsegsdfs(EclFiles.str2deck(schstr))["COMPDAT"]
    assert df["I"].unique() == 33
    assert df["J"].unique() == 44
    assert (df["K1"].values == range(10, 20 + 1)).all()
    assert (df["K2"].values == range(10, 20 + 1)).all()


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-compdat.csv"
    sys.argv = ["compdat2csv", DATAFILE, "-o", tmpcsvfile]
    compdat2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)
