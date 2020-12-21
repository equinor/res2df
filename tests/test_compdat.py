"""Test module for compdat"""

import sys
from pathlib import Path

import pandas as pd

import pytest

from ecl2df import compdat, ecl2csv
from ecl2df import EclFiles

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")

SCHFILE = str(TESTDIR / "data/reek/eclipse/include/schedule/reek_history.sch")

# Reek cases with multisegment well OP_6 including
# AICD and ICD completion from WellBuilder
SCHFILE_AICD = str(TESTDIR / "data/reek/eclipse/include/schedule/op6_aicd1_gp.sch")
SCHFILE_ICD = str(TESTDIR / "data/reek/eclipse/include/schedule/op6_icd1_gp.sch")
SCHFILE_VALV = str(TESTDIR / "data/reek/eclipse/include/schedule/op6_valve1_gp.sch")


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
    tmpcsvfile = tmpdir / "compdat.csv"
    sys.argv = ["ecl2csv", "compdat", "-v", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
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

    assert Path(tmpcsvfile).is_file()
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

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "FIPNUM" in disk_df
    assert "EQLNUM" in disk_df
    assert not disk_df.empty


def test_defaulted_compdat_i_j(tmpdir):
    """I and J can be defaulted (that is 1* or 0) in COMPDAT records, then
    that information should be fetched from the most recent WELSPECS keyword
    """

    welspecs_str = """
WELSPECS
  OP1 OPWEST 20 30 1000 /
/
"""
    compdat_str = """
COMPDAT
  'OP1' 1* 0 10 11  /
/
"""
    compdat_str_nodefaults = """
COMPDAT
  'OP1' 55 66 80 80  /
/
"""

    with pytest.raises(ValueError, match="WELSPECS must be provided"):
        compdat.deck2dfs(EclFiles.str2deck(compdat_str))["COMPDAT"]

    with pytest.raises(ValueError, match="WELSPECS must be provided"):
        # Wrong order:
        compdat.deck2dfs(EclFiles.str2deck(compdat_str + welspecs_str))["COMPDAT"]

    # Simplest example:
    compdat_df = compdat.deck2dfs(EclFiles.str2deck(welspecs_str + compdat_str))[
        "COMPDAT"
    ]
    assert compdat_df["I"].unique() == [20]
    assert compdat_df["J"].unique() == [30]

    # Two wells:
    compdat_df = compdat.deck2dfs(
        EclFiles.str2deck(
            welspecs_str.replace("OP1", "OP2").replace("30", "99")
            + welspecs_str
            + compdat_str
        )
    )["COMPDAT"]

    # Partial defaulting
    compdat_df = compdat.deck2dfs(
        EclFiles.str2deck(welspecs_str + compdat_str + compdat_str_nodefaults)
    )["COMPDAT"]

    assert set(compdat_df["I"].unique()) == {20, 55}
    assert set(compdat_df["J"].unique()) == {30, 66}

    compdat_df = compdat.deck2dfs(
        EclFiles.str2deck(
            welspecs_str.replace("OP1", "OP2").replace("30", "99")
            + welspecs_str
            + compdat_str
            + compdat_str.replace("OP1", "OP2")
        )
    )["COMPDAT"]

    assert compdat_df[compdat_df["WELL"] == "OP1"]["I"].unique() == [20]
    assert compdat_df[compdat_df["WELL"] == "OP2"]["I"].unique() == [20]
    assert compdat_df[compdat_df["WELL"] == "OP1"]["J"].unique() == [30]
    assert compdat_df[compdat_df["WELL"] == "OP2"]["J"].unique() == [99]

    # Same well redrilled to new location
    compdat_df = compdat.deck2dfs(
        EclFiles.str2deck(
            "DATES\n  1 JAN 2030 /\n/\n"
            + welspecs_str
            + compdat_str
            + "DATES\n  1 JAN 2040 /\n/\n"
            + welspecs_str.replace("30", "33")
            + compdat_str
        )
    )["COMPDAT"]
    assert compdat_df[compdat_df["DATE"].astype(str) == "2030-01-01"]["J"].unique() == [
        30
    ]
    assert compdat_df[compdat_df["DATE"].astype(str) == "2040-01-01"]["J"].unique() == [
        33
    ]


# Multisegement well testing
def test_msw_schfile2df():
    """Test that we can process individual files with AICD and ICD MSW"""
    deck = EclFiles.file2deck(SCHFILE_AICD)
    compdfs = compdat.deck2dfs(deck)
    assert not compdfs["WSEGAICD"].empty
    assert not compdfs["WSEGAICD"].columns.empty

    deck = EclFiles.file2deck(SCHFILE_ICD)
    compdfs = compdat.deck2dfs(deck)
    assert not compdfs["WSEGSICD"].empty
    assert not compdfs["WSEGSICD"].columns.empty

    deck = EclFiles.file2deck(SCHFILE_VALV)
    compdfs = compdat.deck2dfs(deck)
    assert not compdfs["WSEGVALV"].empty
    assert not compdfs["WSEGVALV"].columns.empty


def test_msw_str2df():
    """Testing making a dataframe from an explicit string including MSW"""
    schstr = """
WELSPECS
   'OP_6' 'DUMMY' 28 37 1575.82 OIL 0.0 'STD' 'SHUT' 'YES' 0 'SEG' /
/

COMPDAT
    'OP_6' 28 37 1 1 OPEN 0 1.2719 0.311 114.887 0.0 0.0 'X' 19.65 /
/

WELSEGS
-- WELL   SEGMENTTVD  SEGMENTMD WBVOLUME INFOTYPE PDROPCOMP MPMODEL
   'OP_6'        0.0        0.0   1.0E-5    'ABS'     'HF-'    'HO' /
--  SEG  SEG2  BRANCH  OUT MD       TVD       DIAM ROUGHNESS
     2    2    1        1  2371.596 1577.726  0.15 0.00065    /
/

COMPSEGS
   'OP_6' /
--  I   J   K   BRANCH STARTMD  ENDMD    DIR DEF  SEG
    28  37   1   2     2366.541 2376.651  1*  3*  31   /
/

WSEGAICD
-- WELL SEG SEG2   ALPHA    SF  RHO VIS EMU DEF    X    Y
-- FLAG   A   B   C    D    E    F
   OP_6  31   31 1.7e-05 -1.18 1000 1.0 0.5  4* 3.05 0.67
   OPEN 1.0 1.0 1.0 2.43 1.18 10.0  /
/

WSEGSICD
-- WELL   SEG  SEG2 ALPHA  SF             RHO     VIS  WCT
    OP_6  31   31   0.0001  -1.186915444  1000.0  1.0  0.5  /
/

WSEGVALV
-- WELL   SEG             CV      AC   L
    OP_6  31       0.0084252 0.00075  1*  /
/
"""
    deck = EclFiles.str2deck(schstr)
    compdfs = compdat.deck2dfs(deck)
    wsegaicd = compdfs["WSEGAICD"]
    wsegsicd = compdfs["WSEGSICD"]
    wsegvalv = compdfs["WSEGVALV"]

    # Test WSEGAICD
    assert len(wsegaicd) == 1
    assert "WELL" in wsegaicd
    assert wsegaicd["WELL"].unique()[0] == "OP_6"
    assert len(wsegaicd.dropna(axis=1, how="all").iloc[0]) == 19

    # Test WSEGSICD
    assert len(wsegsicd) == 1
    assert "WELL" in wsegsicd
    assert wsegsicd["WELL"].unique()[0] == "OP_6"
    assert len(wsegsicd.dropna(axis=1, how="all").iloc[0]) == 11

    # Test WSEGVALV
    assert len(wsegvalv) == 1
    assert "WELL" in wsegvalv
    assert wsegvalv["WELL"].unique()[0] == "OP_6"
    assert len(wsegvalv.dropna(axis=1, how="all").iloc[0]) == 5

    schstr_valv = """
WELSPECS
   'OP_6' 'DUMMY' 28 37 1575.82 OIL 0.0 'STD' 'SHUT' 'YES' 0 'SEG' /
/

COMPDAT
    'OP_6' 28 37 1 1 OPEN 0 1.2719 0.311 114.887 0.0 0.0 'X' 19.65 /
/

WELSEGS
-- WELL   SEGMENTTVD  SEGMENTMD WBVOLUME INFOTYPE PDROPCOMP MPMODEL
   'OP_6'        0.0        0.0   1.0E-5    'ABS'     'HF-'    'HO' /
--  SEG  SEG2  BRANCH  OUT MD       TVD       DIAM ROUGHNESS
     32    32    1       31  2371.596 1577.726  0.15 0.00065    /
/

COMPSEGS
   'OP_6' /
--  I   J   K   BRANCH STARTMD  ENDMD    DIR DEF  SEG
    28  37   1   2     2366.541 2376.651  1*  3*  32   /
/

-- Max defaulted
WSEGVALV
-- WELL   SEG
    OP_6   31 /
/
"""

    # Test WSEGVALV max defaulted
    deck = EclFiles.str2deck(schstr_valv)
    compdfs = compdat.deck2dfs(deck)
    wsegvalv = compdfs["WSEGVALV"]
    assert len(wsegvalv) == 1
    assert "WELL" in wsegvalv
    assert wsegvalv["WELL"].unique()[0] == "OP_6"
    assert len(wsegvalv.dropna(axis=1, how="all").iloc[0]) == 3

    schstr_valv_wlist = """
WELSPECS
   'OP_6' 'DUMMY' 28 37 1575.82 OIL 0.0 'STD' 'SHUT' 'YES' 0 'SEG' /
   'OP_7' 'DUMMY' 51 15 1675.82 OIL 0.0 'STD' 'SHUT' 'YES' 0 'SEG' /
/

COMPDAT
    'OP_6' 28 37 1 1 OPEN 0 1.2719 0.311 114.887 0.0 0.0 'X' 19.65 /
    'OP_7' 51 15 1 1 OPEN 0 1.2719 0.311 114.887 0.0 0.0 'X' 19.65 /
/

WELSEGS
-- WELL   SEGMENTTVD  SEGMENTMD WBVOLUME INFOTYPE PDROPCOMP MPMODEL
   'OP_6'      1575.82      0.0   1.0E-5    'ABS'     'HF-'    'HO' /
--  SEG  SEG2  BRANCH  OUT MD       TVD       DIAM ROUGHNESS
     2    2     1        1  2371.596 1577.726  0.15 0.00065    /
/

WELSEGS
-- WELL   SEGMENTTVD  SEGMENTMD WBVOLUME INFOTYPE PDROPCOMP MPMODEL
   'OP_7'      1575.82      0.0   1.0E-5    'ABS'     'HF-'    'HO' /
--  SEG  SEG2  BRANCH  OUT MD       TVD       DIAM ROUGHNESS
     2    2     1        1  2071.596 1577.726  0.15 0.00065    /
/

COMPSEGS
   'OP_6' /
--  I   J   K   BRANCH STARTMD  ENDMD    DIR DEF  SEG
    28  37   1   2     2366.541 2376.651  1*  3*   2   /
/
COMPSEGS
   'OP_7' /
--  I   J   K   BRANCH STARTMD  ENDMD    DIR DEF  SEG
    51  15   1   2     2080.541 2099.651  1*  3*    2   /
/

WLIST
-- NAME  OPERATION      WELLS
 OPRODS        NEW  OP_6 OP_7
/

-- Max defaulted with well list
WSEGVALV
-- LIST   SEG
 OPRODS   31 /
/
"""

    # Test WSEGVALV max defaulted and wlist
    deck = EclFiles.str2deck(schstr_valv_wlist)
    compdfs = compdat.deck2dfs(deck)
    wsegvalv = compdfs["WSEGVALV"]
    assert len(wsegvalv) == 0
    assert "WELL" not in wsegvalv
