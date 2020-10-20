"""Test module for nnc"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd

import pytest

from ecl2df import compdat, ecl2csv
from ecl2df import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")

SCHFILE = os.path.join(TESTDIR, "./data/reek/eclipse/include/schedule/reek_history.sch")


def test_df():
    """Test main dataframe API, only testing that something comes out"""
    eclfiles = EclFiles(DATAFILE)
    compdat_df = compdat.df(eclfiles)
    assert not compdat_df.empty
    assert "ZONE" in compdat_df
    assert "K1" in compdat_df
    assert "WELL" in compdat_df


def test_comp2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    compdfs = compdat.deck2dfs(eclfiles.get_ecldeck())

    assert not compdfs["COMPDAT"].empty
    assert compdfs["WELSEGS"].empty  # REEK demo does not include multisegment wells
    assert compdfs["COMPSEGS"].empty
    assert not compdfs["COMPDAT"].columns.empty


def test_schfile2df():
    """Test that we can process individual files"""
    deck = EclFiles.file2deck(SCHFILE)
    compdfs = compdat.deck2dfs(deck)
    assert not compdfs["COMPDAT"].columns.empty
    assert not compdfs["COMPDAT"].empty


def test_str_compdat():
    """Test compdat parsing directly on strings"""
    schstr = """
COMPDAT
 'OP1' 33 110 31 31 'OPEN' 1* 6467.31299 0.216 506642.25  0 1* 'Y' 7.18 /
-- comments.
/
"""
    deck = EclFiles.str2deck(schstr)
    compdfs = compdat.deck2dfs(deck)
    compdat_df = compdfs["COMPDAT"]
    assert compdat_df.loc[0, "SATN"] == 0
    assert not compdat_df.loc[0, "DFACT"]
    assert compdat_df.loc[0, "DIR"] == "Y"

    schstr = """
COMPDAT
 'FOO' 303 1010 031 39  /
/
"""
    compdat_df = compdat.deck2dfs(EclFiles.str2deck(schstr))["COMPDAT"]
    assert len(compdat_df) == 9
    assert not compdat_df["DFACT"].values[0]
    assert not compdat_df["TRAN"].values[0]
    assert compdat_df["I"].values[0] == 303


def test_str2df():
    """Testing making a dataframe from an explicit string"""
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
    compdfs = compdat.deck2dfs(deck)
    compdat_df = compdfs["COMPDAT"]
    welsegs = compdfs["WELSEGS"]
    compsegs = compdfs["COMPSEGS"]
    assert "WELL" in compdat_df
    assert len(compdat_df) == 1
    assert compdat_df["WELL"].unique()[0] == "OP1"

    # Check that we have not used the very long opm.io term here:
    assert "CONNECTION_TRANSMISSIBILITY_FACTOR" not in compdat_df
    assert "TRAN" in compdat_df

    assert "Kh" not in compdat_df  # Mixed-case should not be used.
    assert "KH" in compdat_df

    # Make sure the ' are ignored:
    assert compdat_df["OP/SH"].unique()[0] == "OPEN"

    # Continue to WELSEGS
    assert len(welsegs) == 1  # First record is appended to every row.

    # Since we have 'ABS' in WELSEGS, there should be an extra
    # column called 'SEGMENT_MD'
    assert "SEGMENT_MD" in welsegs
    assert welsegs["SEGMENT_MD"].max() == 1923.9

    # Test COMPSEGS
    assert len(compsegs) == 1
    assert "WELL" in compsegs
    assert compsegs["WELL"].unique()[0] == "OP1"
    assert len(compsegs.dropna(axis=1, how="all").iloc[0]) == 8

    # Check date handling
    assert "DATE" in compdat_df
    assert not all(compdat_df["DATE"].notna())
    compdat_date = compdat.deck2dfs(deck, start_date="2000-01-01")["COMPDAT"]
    assert "DATE" in compdat_date
    assert all(compdat_date["DATE"].notna())
    assert len(compdat_date["DATE"].unique()) == 1
    assert str(compdat_date["DATE"].unique()[0]) == "2000-01-01"


def test_tstep():
    """Test with TSTEP present"""
    schstr = """
DATES
   1 MAY 2001 /
/

COMPDAT
 'OP1' 33 110 31 31 'OPEN'  /
/

TSTEP
  1 /

COMPDAT
 'OP1' 34 111 32 32 'OPEN' /
/

TSTEP
  2 3 /

COMPDAT
  'OP1' 35 111 33 33 'SHUT' /
/
"""
    deck = EclFiles.str2deck(schstr)
    compdf = compdat.deck2dfs(deck)["COMPDAT"]
    dates = [str(x) for x in compdf["DATE"].unique()]
    assert len(dates) == 3
    assert "2001-05-01" in dates
    assert "2001-05-02" in dates
    assert "2001-05-07" in dates


def test_applywelopen():
    schstr = """
DATES
   1 MAY 2001 /
/

COMPDAT
 'OP1' 33 110 31 31 'OPEN'  /
/
WELOPEN
 'OP1' 'SHUT' /
/

TSTEP
  1 /

COMPDAT
 'OP2' 66 110 31 31 'OPEN'  /
/

WELOPEN
 'OP1' 'OPEN' /
/

TSTEP
  2 3 /

WELOPEN
 'OP1' 'POPN' /
 'OP2' 'SHUT' /
/
"""
    df = compdat.deck2dfs(EclFiles.str2deck(schstr))["COMPDAT"]
    assert df.shape[0] == 5
    assert df["OP/SH"].nunique() == 2
    assert df["DATE"].nunique() == 3

    schstr = """
DATES
   1 MAY 2001 /
/

COMPDAT
 'OP1' 33 110 31 31 'OPEN'  /
/
WELOPEN
 'OP2' 'SHUT' /
/"""
    with pytest.raises(ValueError):
        compdat.deck2dfs(EclFiles.str2deck(schstr))["COMPDAT"]


def test_unrollcompdatk1k2():
    """Test unrolling of k1-k2 ranges in COMPDAT"""
    schstr = """
COMPDAT
  -- K1 to K2 is a range of 11 layers, should be automatically
  -- unrolled to 11 rows.
  'OP1' 33 44 10 20  /
/
"""
    df = compdat.deck2dfs(EclFiles.str2deck(schstr))["COMPDAT"]
    assert df["I"].unique() == 33
    assert df["J"].unique() == 44
    assert (df["K1"].values == range(10, 20 + 1)).all()
    assert (df["K2"].values == range(10, 20 + 1)).all()

    # Check that we can read withoug unrolling:
    df_noroll = compdat.deck2dfs(EclFiles.str2deck(schstr), unroll=False)["COMPDAT"]
    assert len(df_noroll) == 1


def test_unrollwelsegs():
    """Test unrolling of welsegs."""
    schstr = """
WELSEGS
  -- seg_start to seg_end (two first items in second record) is a range of
  -- 2 segments, should be automatically unrolled to 2 rows.
  'OP1' 1689 1923 1.0E-5 'ABS' 'HFA' 'HO' / comment without -- identifier
   2 3 1 1 1923.9 1689.000 0.1172 0.000015  /
/
"""
    df = compdat.deck2dfs(EclFiles.str2deck(schstr))["WELSEGS"]
    assert len(df) == 2

    df = compdat.deck2dfs(EclFiles.str2deck(schstr), unroll=False)["WELSEGS"]
    assert len(df) == 1


def test_unrollbogus():
    """Giving in empty dataframe, should not crash."""
    assert compdat.unrolldf(pd.DataFrame).empty

    bogusdf = pd.DataFrame([0, 1, 4], [0, 2, 5])
    unrolled = compdat.unrolldf(pd.DataFrame([0, 1, 4], [0, 2, 5]), "FOO", "bar")
    # (warning should be issued)
    assert (unrolled == bogusdf).all().all()


def test_initmerging():
    """Test that we can ask for INIT vectors to be merged into the data"""
    eclfiles = EclFiles(DATAFILE)
    noinit_df = compdat.df(eclfiles)
    df = compdat.df(eclfiles, initvectors=[])
    assert isinstance(df, pd.DataFrame)
    assert not df.empty

    df = compdat.df(eclfiles, initvectors=["FIPNUM", "EQLNUM", "SATNUM"])
    assert "FIPNUM" in df
    assert "EQLNUM" in df
    assert "SATNUM" in df
    assert len(df) == len(noinit_df)

    df = compdat.df(eclfiles, initvectors="FIPNUM")
    assert "FIPNUM" in df
    assert len(df) == len(noinit_df)

    with pytest.raises(AssertionError):
        compdat.df(eclfiles, initvectors=2)


def test_main_subparsers(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-compdat.csv")
    sys.argv = ["ecl2csv", "compdat", "-v", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()

    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "ZONE" in disk_df
    assert not disk_df.empty

    sys.argv = [
        "ecl2csv",
        "compdat",
        DATAFILE,
        "--initvectors",
        "FIPNUM",
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()

    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "FIPNUM" in disk_df
    assert not disk_df.empty

    sys.argv = [
        "ecl2csv",
        "compdat",
        DATAFILE,
        "--initvectors",
        "FIPNUM",
        "EQLNUM",
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()

    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "FIPNUM" in disk_df
    assert "EQLNUM" in disk_df
    assert not disk_df.empty
