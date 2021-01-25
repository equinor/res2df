"""Test module for satfunc2df"""

import subprocess
from pathlib import Path

import pytest

import pandas as pd

from ecl2df import satfunc, ecl2csv, csv2ecl, inferdims
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


def test_df2ecl_order():
    """Test that we can control the keyword order in generated
    strings by the list supplied in keywords argument"""
    eclfiles = EclFiles(DATAFILE)
    satdf = satfunc.df(eclfiles.get_ecldeck())

    swof_sgof = satfunc.df2ecl(satdf, keywords=["SWOF", "SGOF"])
    assert swof_sgof.find("SWOF") < swof_sgof.find("SGOF")
    sgof_swof = satfunc.df2ecl(satdf, keywords=["SGOF", "SWOF"])
    assert sgof_swof.find("SGOF") < sgof_swof.find("SWOF")

    only_swof = satfunc.df2ecl(satdf, keywords=["SWOF"])
    assert "SGOF" not in only_swof
    only_sgof = satfunc.df2ecl(satdf, keywords="SGOF")
    assert "SWOF" not in only_sgof


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


def test_sgof_satnuminferrer(tmpdir, mocker):
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
    Path(sgoffile).write_text(sgofstr)
    mocker.patch(
        "sys.argv", ["ecl2csv", "satfunc", "-v", sgoffile, "-o", sgoffile + ".csv"]
    )
    ecl2csv.main()
    parsed_sgof = pd.read_csv(sgoffile + ".csv")
    assert len(parsed_sgof["SATNUM"].unique()) == 3


def test_wrong_columns():
    """Test some error situations"""
    # SWFN data given as SWOF:
    satnumstr = """
SWOF
0 0 0
1 1 0
/
"""
    with pytest.raises(ValueError, match="Wrong number count for keyword SWOF"):
        satfunc.df(satnumstr)
    satnumstr = """
SWFN
0 0 0 0
1 1 0 0
/
"""
    with pytest.raises(ValueError, match="Wrong number count for keyword SWFN"):
        satfunc.df(satnumstr)

    # The following error is parseable into a dataframe, but gives
    # four saturation points, this error can not be detected while parsing.
    satnumstr = """
SWFN
0 0 0 0
0.5 0.5 0.5 0
1 1 0 0
/
"""
    wrongdf = satfunc.df(satnumstr)
    # We see the error as the saturation points are not unique:
    assert len(wrongdf["SW"]) == 4
    assert len(wrongdf["SW"].unique()) == 3


def test_multiple_keywords_family2():

    satnumstr = """
SWFN
-- Sw           Krw           Pcow
  0 0 2
  1.   1.000   0.00000e+00
/

SOF3
-- So           Krow          Krog
   0.00000e+00   0.00000e+00   0.00000e+00
   0.581051658   1.000000000   1.000000000
/

SGFN
-- Sg    Krg      Pcog
  0.000  0.00000  0.000
  0.800  1.00000  0.000
/
    """
    satnum_df = satfunc.df(satnumstr)
    assert set(satnum_df["SATNUM"]) == {1}
    assert set(satnum_df["KEYWORD"]) == {"SWFN", "SOF3", "SGFN"}
    assert len(satnum_df) == 6


def test_main_subparsers(tmpdir, mocker):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join("satfunc.csv")
    mocker.patch("sys.argv", ["ecl2csv", "satfunc", DATAFILE, "-o", str(tmpcsvfile)])
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty

    tmpcsvfile2 = tmpdir.join(".TMP-satfunc-swof.csv")
    print(tmpcsvfile2)
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "satfunc",
            DATAFILE,
            "--keywords",
            "SWOF",
            "--output",
            str(tmpcsvfile2),
        ],
    )
    ecl2csv.main()

    assert Path(tmpcsvfile2).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile2))
    assert set(disk_df["KEYWORD"].unique()) == {"SWOF"}


def test_csv2ecl(tmpdir, mocker):
    """Test command line interface for csv to Eclipse include files"""
    tmpdir.chdir()
    tmpcsvfile = "satfunc.csv"

    swof_df = pd.DataFrame(
        columns=["KEYWORD", "SW", "KRW", "KROW", "PCOW"],
        data=[["SWOF", 0.0, 0.0, 1.0, 0.0], ["SWOF", 1.0, 1.0, 0.0, 0.0]],
    )
    swof_df.to_csv(tmpcsvfile, index=False)
    mocker.patch("sys.argv", ["csv2ecl", "satfunc", "--output", "swof.inc", tmpcsvfile])
    csv2ecl.main()
    pd.testing.assert_frame_equal(
        satfunc.df(open("swof.inc").read()).drop("SATNUM", axis="columns"),
        swof_df,
        check_like=True,
    )

    # Test writing to stdout:
    result = subprocess.run(
        ["csv2ecl", "satfunc", "--output", "-", tmpcsvfile], stdout=subprocess.PIPE
    )
    pd.testing.assert_frame_equal(
        satfunc.df(result.stdout.decode()).drop("SATNUM", axis="columns"),
        swof_df,
        check_like=True,
    )
