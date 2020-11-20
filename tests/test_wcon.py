"""Test module for wcon"""

import sys
from pathlib import Path

import pandas as pd

from ecl2df import wcon, ecl2csv
from ecl2df.eclfiles import EclFiles
from ecl2df.wcon import unroll_defaulted_items, ad_hoc_wconparser

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_unroller():
    """Test that the defaults unroller is correct"""
    assert len(unroll_defaulted_items(["3*"])) == 3
    assert not unroll_defaulted_items(["0*"])
    assert len(unroll_defaulted_items(["1*"])) == 1
    assert len(unroll_defaulted_items(["99*"])) == 99
    assert len(unroll_defaulted_items(["-1*"])) == 1
    assert len(unroll_defaulted_items(["foo", "2*", "bar"])) == 4
    assert unroll_defaulted_items(["foo", "2*", "bar"])[1] == "1*"
    assert unroll_defaulted_items(["foo", "2*", "bar"])[2] == "1*"


def test_ad_hoc_wconparser():
    """This is the temporary parser that we need until opm-common is
    up to speed"""
    items = ad_hoc_wconparser(
        (
            "'OP_2'  OPEN  RESV 3862.069 94.14519 710620.7 "
            "   1*       1*       1*       1* "
        ),
        "WCONPROD",
    )
    print(items)
    assert items["WELL"] == "OP_2"
    assert items["STATUS"] == "OPEN"
    assert items["CMODE"] == "RESV"
    assert int(items["ORAT"]) == 3862
    assert int(items["WRAT"]) == 94
    assert int(items["GRAT"]) == 710620
    assert int(items["RESV"]) == 0  # default value exists.
    assert items["BHP"] == 1.01325  # default value
    # VFP_TABLE is not here, because it was not mentioned.
    # Not sure if we should have the default value
    # in the returned data or just ignore it.

    items = ad_hoc_wconparser(
        "'OP_1'  OPEN  RESV 3833.858 50.36119 705429.9 ", "WCONHIST"
    )
    print(items)
    assert items["WELL"] == "OP_1"
    assert items["GRAT"] == 705429.9


def test_wcon2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    wcondf = wcon.df(eclfiles.get_ecldeck())

    assert not wcondf.empty
    assert "DATE" in wcondf  # for all data
    assert "KEYWORD" in wcondf
    for col in wcondf.columns:
        assert col == col.upper()


def test_str2df():
    """Test dataframe extraction from strings"""
    wconstr = """
WCONHIST
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wcondf = wcon.df(deck)
    assert len(wcondf) == 1

    wconstr = """
WCONINJH
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wcondf = wcon.df(deck)
    assert len(wcondf) == 1

    wconstr = """
WCONINJE
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wcondf = wcon.df(deck)
    assert len(wcondf) == 1

    wconstr = """
WCONPROD
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wcondf = wcon.df(deck)
    assert len(wcondf) == 1


def test_tstep():
    """Test that we support the TSTEP keyword"""
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
    wcondf = wcon.df(deck)
    dates = [str(x) for x in wcondf["DATE"].unique()]
    assert len(dates) == 3
    assert "2001-05-01" in dates
    assert "2001-05-02" in dates
    assert "2001-05-07" in dates


def test_main_subparsers(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir / ".TMP-wcondf.csv"
    sys.argv = ["ecl2csv", "wcon", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
