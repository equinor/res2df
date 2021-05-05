"""Test module for satfunc2df"""

import subprocess
from pathlib import Path

import pytest

import numpy as np
import pandas as pd

from ecl2df import satfunc, ecl2csv, csv2ecl, inferdims
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_ecldeck_to_satfunc_dframe():
    """Test that dataframes can be produced from a full Eclipse deck (the
    example Reek case)"""
    eclfiles = EclFiles(DATAFILE)
    satdf = satfunc.df(eclfiles.get_ecldeck())

    assert set(satdf["KEYWORD"]) == {"SWOF", "SGOF"}
    assert set(satdf["SATNUM"]) == {1}

    assert np.isclose(satdf["SW"].min(), 0.32)
    assert np.isclose(satdf["SW"].max(), 1.0)

    assert np.isclose(satdf["SG"].min(), 0.0)
    assert np.isclose(satdf["SG"].max(), 1 - 0.32)

    assert np.isclose(satdf["KRW"].min(), 0.0)
    assert np.isclose(satdf["KRW"].max(), 1.0)

    assert np.isclose(satdf["KROW"].min(), 0.0)
    assert np.isclose(satdf["KROW"].max(), 1.0)

    assert np.isclose(satdf["KROG"].min(), 0.0)
    assert np.isclose(satdf["KROG"].max(), 1.0)

    assert len(satdf) == 76


def test_satfunc_roundtrip():
    """Test that we can produce a SATNUM dataframe from the Reek case, convert
    it back to an include file, and then reinterpret it to the same"""
    eclfiles = EclFiles(DATAFILE)
    satdf = satfunc.df(eclfiles.get_ecldeck())
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


@pytest.mark.parametrize(
    "string, expected_df",
    [
        ("", pd.DataFrame()),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            """SWOF
  0 0 1 1
  1 1 0 0
/
""",
            pd.DataFrame(
                columns=["SW", "KRW", "KROW", "PCOW", "SATNUM", "KEYWORD"],
                data=[[0.0, 0.0, 1.0, 1.0, 1, "SWOF"], [1.0, 1.0, 0.0, 0.0, 1, "SWOF"]],
            ),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            """
RUNSPEC -- (this line is optional)

TABDIMS
  2/

PROPS -- (optional)

SWOF
  0 0 1 1
  1 1 0 0
/
  0 0 1 1
  0.5 0.5 0.5 0.5
  1 1 0 0
/
""",
            pd.DataFrame(
                columns=["SW", "KRW", "KROW", "PCOW", "SATNUM", "KEYWORD"],
                data=[
                    [0.0, 0.0, 1.0, 1.0, 1, "SWOF"],
                    [1.0, 1.0, 0.0, 0.0, 1, "SWOF"],
                    [0.0, 0.0, 1.0, 1.0, 2, "SWOF"],
                    [0.5, 0.5, 0.5, 0.5, 2, "SWOF"],
                    [1.0, 1.0, 0.0, 0.0, 2, "SWOF"],
                ],
            ),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        ("SWRF\n0 / \n", pd.DataFrame()),  # a warning will be printed
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            # Bogus E100 keywords, will be accepted:
            "FOO\n\nSWOF\n 0 0 1 1\n 1 1  0 0\n/\n",
            pd.DataFrame(
                columns=["SW", "KRW", "KROW", "PCOW", "SATNUM", "KEYWORD"],
                data=[[0.0, 0.0, 1.0, 1.0, 1, "SWOF"], [1.0, 1.0, 0.0, 0.0, 1, "SWOF"]],
            ),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            """SLGOF
  0 1 1 0
  1 0 0 0
/
    """,
            pd.DataFrame(
                columns=["SL", "KRG", "KRO", "PCOG", "SATNUM", "KEYWORD"],
                data=[
                    [0.0, 1.0, 1.0, 0.0, 1, "SLGOF"],
                    [1.0, 0.0, 0.0, 0.0, 1, "SLGOF"],
                ],
            ),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            """SOF2
  0 1
  1 0
/
""",
            pd.DataFrame(
                columns=["SO", "KRO", "SATNUM", "KEYWORD"],
                data=[
                    [0.0, 1.0, 1, "SOF2"],
                    [1.0, 0.0, 1, "SOF2"],
                ],
            ),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            """SOF3
  0 1 1
  1 0 0
/
""",
            pd.DataFrame(
                columns=["SO", "KROW", "KROG", "SATNUM", "KEYWORD"],
                data=[
                    [0.0, 1.0, 1.0, 1, "SOF3"],
                    [1.0, 0.0, 0.0, 1, "SOF3"],
                ],
            ),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            """
SGFN
  0 1 0
  1 0 0
/
  0 1 0
  1 0.1 1
/
""",
            pd.DataFrame(
                columns=["SG", "KRG", "PCOG", "SATNUM", "KEYWORD"],
                data=[
                    [0.0, 1.0, 0.0, 1, "SGFN"],
                    [1.0, 0.0, 0.0, 1, "SGFN"],
                    [0.0, 1.0, 0.0, 2, "SGFN"],
                    [1.0, 0.1, 1.0, 2, "SGFN"],
                ],
            ),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            """SGWFN
  0 1 1 0
  1 0 0 0
 /
 """,
            pd.DataFrame(
                columns=["SG", "KRG", "KRW", "PCGW", "SATNUM", "KEYWORD"],
                data=[
                    [0.0, 1.0, 1.0, 0.0, 1, "SGWFN"],
                    [1.0, 0.0, 0.0, 0.0, 1, "SGWFN"],
                ],
            ),
        ),
    ],
)
def test_str2df(string, expected_df):
    """Test that we can parse a string into a DataFrame,
    back to string, and to DataFrame again"""
    satdf = satfunc.df(string)
    pd.testing.assert_frame_equal(satdf, expected_df)

    if expected_df.empty:
        return

    inc = satfunc.df2ecl(satdf)
    df_from_inc = satfunc.df(inc)
    pd.testing.assert_frame_equal(df_from_inc, expected_df)


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
