"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd

from ecl2df import gruptree, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_gruptree2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    grupdf = gruptree.df(eclfiles.get_ecldeck())

    assert not grupdf.empty
    assert len(grupdf["DATE"].unique()) == 5
    assert len(grupdf["CHILD"].unique()) == 10
    assert len(grupdf["PARENT"].unique()) == 3
    assert set(grupdf["KEYWORD"].unique()) == set(["GRUPTREE", "WELSPECS"])

    grupdfnowells = gruptree.df(eclfiles.get_ecldeck(), welspecs=False)

    assert len(grupdfnowells["KEYWORD"].unique()) == 1
    assert grupdf["PARENT"].unique()[0] == "FIELD"
    assert grupdf["KEYWORD"].unique()[0] == "GRUPTREE"


def test_str2df():
    """Test when we send in a string directly"""
    schstr = """
GRUPTREE
 'OPWEST' 'OP' /
 'OP' 'FIELD' /
 'FIELD' 'AREA' /
 'AREA' 'NORTHSEA' /
/

WELSPECS
 'OP1' 'OPWEST' 41 125 1759.74 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
/

"""
    deck = EclFiles.str2deck(schstr)
    grupdf = gruptree.df(deck)
    assert grupdf.dropna().empty  # the DATE is empty

    # This is only available if GRUPNET is also there
    assert "TERMINAL_PRESSURE" not in grupdf

    withstart = gruptree.df(deck, startdate="2019-01-01")
    assert not withstart.dropna().empty
    assert len(withstart) == 5


def test_grupnet_rst_docs(tmpdir):
    """Provide the input and output for the examples in the RST documentation"""
    tmpdir.chdir()
    schstr = """
START
 01 'JAN' 2000 /

SCHEDULE

GRUPTREE
 'OPEAST' 'OP' /
 'OPWEST' 'OP' /
 'INJEAST' 'WI' /
 'OP' 'FIELD' /
 'WI' 'FIELD' /
 'FIELD' 'AREA' /
 'AREA' 'NORTHSEA' /
/

GRUPNET
  'FIELD' 90 /
  'OPWEST' 100 /
/

WELSPECS
 'OP1'  'OPWEST'  41 125 1759.74 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
 'OP2'  'OPEAST'  43 122 1776.01 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
 'INJ1' 'INJEAST' 33 115 1960.21 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
/

"""
    deck = EclFiles.str2deck(schstr)
    grupdf = gruptree.df(deck)
    grupdf[["DATE", "CHILD", "PARENT", "KEYWORD"]].to_csv("gruptree.csv", index=False)
    grupdf.to_csv("gruptreenet.csv", index=False)
    grup_dict = gruptree.edge_dataframe2dict(grupdf)
    print("Copy and paste into RST files:")
    print(str(gruptree.dict2treelib("", grup_dict[0])))


def test_grupnetdf():
    """Test making a dataframe from a GRUPTREE string"""
    schstr = """
GRUPTREE
 'OPWEST' 'OP' /
 'OP' 'FIELD' /
 'WI' 'FIELD' /
 'FIELD' 'AREA' /
 'AREA' 'NORTHSEA' /
/

GRUPNET
  'FIELD' 90 /
  'OPWEST' 100 /
/

"""
    deck = EclFiles.str2deck(schstr)
    grupdf = gruptree.df(deck, startdate="2000-01-01")
    print(grupdf)
    assert "TERMINAL_PRESSURE" in grupdf
    assert 90 in grupdf["TERMINAL_PRESSURE"].values
    assert 100 in grupdf["TERMINAL_PRESSURE"].values


def test_emptytree():
    """Test empty schedule sections. Don't want to crash"""
    schstr = ""
    deck = EclFiles.str2deck(schstr)
    grupdf = gruptree.df(deck)
    assert grupdf.empty
    gruptreedict = gruptree.edge_dataframe2dict(grupdf)
    assert not gruptreedict[0]
    treelibtree = gruptree.dict2treelib("", gruptreedict[0])
    treestring = str(treelibtree)
    assert not treestring.strip()  # Let it return whitespace


def test_tstep():
    """Test that we can parse a deck using TSTEP for timestepping"""
    schstr = """
GRUPTREE
 'OPWEST' 'OP' /
 'OP' 'FIELD' /
 'FIELD' 'AREA' /
 'AREA' 'NORTHSEA' /
/

TSTEP
  1 /

WELSPECS
 'OP1' 'OPWEST' 41 125 1759.74 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
/

"""
    deck = EclFiles.str2deck(schstr)
    grupdf = gruptree.df(deck)
    assert len(grupdf["DATE"].unique()) == 2
    print(grupdf)


def test_main(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-gruptree.csv")
    sys.argv = ["ecl2csv", "gruptree", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()

    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty


def test_prettyprint():
    """Test pretty printing via command line interface"""
    sys.argv = ["ecl2csv", "gruptree", DATAFILE, "--prettyprint"]
    ecl2csv.main()


def test_main_subparser(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-gruptree.csv")
    sys.argv = ["ecl2csv", "gruptree", "-v", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()

    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
