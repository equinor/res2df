"""Test module for satfunc2df"""

import sys
from pathlib import Path

import pandas as pd

from ecl2df import satfunc, ecl2csv, inferdims
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_satfunc2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    satdf = satfunc.df(eclfiles.get_ecldeck())

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

    inc = satfunc.df2ecl(satdf)
    df_from_inc = satfunc.df(inc)
    pd.testing.assert_frame_equal(
        satdf.sort_values(["SATNUM", "KEYWORD"]),
        df_from_inc.sort_values(["SATNUM", "KEYWORD"]),
    )


def test_nodata():
    """Test when no data is found"""
    swofstr = ""

    satdf = satfunc.df(swofstr)
    assert len(satdf) == 0

    inc = satfunc.df2ecl_swof(satdf)
    assert "No data" in inc
    df_from_inc = satfunc.df(inc)
    assert df_from_inc.empty


def test_str2df():
    """Test parsing of a direct string"""
    swofstr = """
SWOF
 0 0 1 1
 1 1 0 0
 /
"""
    satdf = satfunc.df(swofstr)
    assert len(satdf) == 2
    inc = satfunc.df2ecl_swof(satdf)
    df_from_inc = satfunc.df(inc)
    pd.testing.assert_frame_equal(satdf, df_from_inc)

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
    satdf2 = satfunc.df(swofstr2)
    assert "SATNUM" in satdf
    assert len(satdf2["SATNUM"].unique()) == 2
    assert len(satdf2) == 5

    inc = satfunc.df2ecl(satdf)
    df_from_inc = satfunc.df(inc)
    pd.testing.assert_frame_equal(satdf, df_from_inc)

    # Try empty/bogus data:
    bogusdf = satfunc.df("SWRF\n 0 /\n")
    # (warnings should be issued)
    assert bogusdf.empty

    # Test with bogus E100 keywords:
    tricky = satfunc.df("FOO\n\nSWOF\n 0 0 0 1/ 1 1 1 0\n/\n")
    assert not tricky.empty
    assert len(tricky["SATNUM"].unique()) == 1

    # Test with unsupported (for OPM) E100 keywords (trickier than bogus..)
    # # tricky = satfunc.df("CARFIN\n\nSWOF\n 0 0 0 1/ 1 1 1 0\n/\n")
    # # assert not tricky.empty
    # # assert len(tricky["SATNUM"].unique()) == 1
    # ### It remains unsolved how to avoid an error here!


def test_slgof(tmpdir):
    """Test parsing of SLGOF"""
    tmpdir.chdir()
    string = """
SLGOF
  0 1 1 0
  1 0 0 0
/
"""
    slgof_df = satfunc.df(string)
    assert len(slgof_df) == 2
    assert "SL" in slgof_df
    assert "KRG" in slgof_df
    assert "KRO" in slgof_df
    assert "PCOG" in slgof_df
    inc = satfunc.df2ecl(slgof_df, filename="slgof.inc")
    assert Path("slgof.inc").is_file()
    df_from_inc = satfunc.df(inc)
    pd.testing.assert_frame_equal(slgof_df, df_from_inc)


def test_sof2():
    """Test parsing of SOF2"""
    string = """
SOF2
  0 1
  1 0
/
"""
    sof2_df = satfunc.df(string)
    assert len(sof2_df) == 2
    assert "SO" in sof2_df
    assert "KRO" in sof2_df
    inc = satfunc.df2ecl(sof2_df)
    df_from_inc = satfunc.df(inc)
    pd.testing.assert_frame_equal(sof2_df, df_from_inc)


def test_sof3():
    """Test parsing of SOF3"""
    string = """
SOF3
  0 1 1
  1 0 0
/
"""
    sof3_df = satfunc.df(string)
    assert len(sof3_df) == 2
    assert "SO" in sof3_df
    assert "KROW" in sof3_df
    assert "KROG" in sof3_df
    inc = satfunc.df2ecl(sof3_df)
    df_from_inc = satfunc.df(inc)
    pd.testing.assert_frame_equal(sof3_df, df_from_inc)


def test_sgfn():
    """Test parsing of SGFN"""
    string = """
SGFN
  0 1 0
  1 0 0
/
  0 1 0
  1 0.1 1
/
"""
    sgfn_df = satfunc.df(string)
    assert len(sgfn_df) == 4
    assert len(sgfn_df["SATNUM"].unique()) == 2
    assert "SG" in sgfn_df
    assert "KRG" in sgfn_df
    assert "PCOG" in sgfn_df
    inc = satfunc.df2ecl(sgfn_df)
    df_from_inc = satfunc.df(inc)
    pd.testing.assert_frame_equal(sgfn_df, df_from_inc)


def test_sgwfn():
    """Test parsing of SGWFN"""
    string = """
 SGWFN
  0 1 1 0
  1 0 0 0
 /
 """
    sgwfn_df = satfunc.df(string)
    assert len(sgwfn_df) == 2
    assert "SG" in sgwfn_df
    assert "KRG" in sgwfn_df
    assert "KRW" in sgwfn_df
    assert "PCGW" in sgwfn_df
    inc = satfunc.df2ecl(sgwfn_df)
    df_from_inc = satfunc.df(inc)
    pd.testing.assert_frame_equal(
        sgwfn_df.sort_values(["SATNUM", "KEYWORD"]),
        df_from_inc.sort_values(["SATNUM", "KEYWORD"]),
    )


def test_sgof_satnuminferrer(tmpdir):
    """Test inferring of SATNUMS in SGOF strings"""
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
    tmpdir.chdir()
    assert inferdims.guess_dim(sgofstr, "TABDIMS", 0) == 3
    sgofdf = satfunc.df(sgofstr)
    assert "SATNUM" in sgofdf
    assert len(sgofdf["SATNUM"].unique()) == 3
    assert len(sgofdf) == 8
    inc = satfunc.df2ecl(sgofdf)
    df_from_inc = satfunc.df(inc)
    pd.testing.assert_frame_equal(sgofdf, df_from_inc)

    # Write to file and try to parse it with command line:
    sgoffile = "__sgof_tmp.txt"
    with open(sgoffile, "w") as sgof_f:
        sgof_f.write(sgofstr)

    sys.argv = ["ecl2csv", "satfunc", "-v", sgoffile, "-o", sgoffile + ".csv"]
    ecl2csv.main()
    parsed_sgof = pd.read_csv(sgoffile + ".csv")
    assert len(parsed_sgof["SATNUM"].unique()) == 3


def test_main_subparsers(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-satfunc.csv")
    sys.argv = ["ecl2csv", "satfunc", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty

    tmpcsvfile2 = tmpdir.join(".TMP-satfunc-swof.csv")
    print(tmpcsvfile2)
    sys.argv = [
        "ecl2csv",
        "satfunc",
        DATAFILE,
        "--keywords",
        "SWOF",
        "--output",
        str(tmpcsvfile2),
    ]
    ecl2csv.main()

    assert Path(tmpcsvfile2).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile2))
    assert set(disk_df["KEYWORD"].unique()) == {"SWOF"}
