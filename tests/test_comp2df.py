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

from ecl2df import compdat2df
from ecl2df.eclfiles import EclFiles

DATAFILE = "data/reek/eclipse/model/2_R001_REEK-0.DATA"
SCHFILE = "./data/reek/eclipse/include/schedule/reek_history.sch"

def test_comp2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    compdfs = compdat2df.deck2compdatsegsdfs(eclfiles.get_ecldeck())

    assert not compdfs[0].empty
    assert compdfs[1].empty  # REEK demo does not include multisegment wells
    assert compdfs[2].empty
    assert len(compdfs[0].columns)


def test_schfile2df():
    """Test that we can process individual files"""
    deck = EclFiles.file2deck(SCHFILE)
    compdfs = compdat2df.deck2compdatsegsdfs(deck)
    assert len(compdfs[0].columns)
    assert not compdfs[0].empty


def test_str2df():
    schstr = """
WELSPECS
 'OP1' 'OPWEST' 41 125 1759.74 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
/

COMPDAT
 'OP1' 33 110 31 31 'OPEN' 0 6467.31299 0.216 506642.25  0.0 0.0 'Y' 7.18 /
/

WELSEGS
  'OP1' 1689 1923 1.0E-5 'ABS' 'HFA' 'HO' /
   2 2 1 1 1923.9 1689.000 0.1172 0.000015  /
/

COMPSEGS
  'OP1' /
  41 125 29  5 2577.0 2616.298 / icd on branch 1 in segment 17
/
WSEGVALV
  'OP1'   166   1   7.4294683E-06  0 / icd on segment 17, cell 41 125 29
/
"""
    deck = EclFiles.str2deck(schstr)
    compdfs = compdat2df.deck2compdatsegsdfs(deck)
    print(compdfs[0])
    print(compdfs[1])
    print(compdfs[2])


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-compdat.csv"
    sys.argv = ["compdat2csv", DATAFILE, "-o", tmpcsvfile]
    compdat2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)
