"""Test module for equil2df"""

import subprocess
from pathlib import Path

import pytest

import numpy as np
import pandas as pd

from ecl2df import equil, ecl2csv, csv2ecl
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_equil2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    equildf = equil.df(eclfiles)
    expected = {}
    expected["EQUIL"] = pd.DataFrame(
        [
            {
                "Z": 2469.0,
                "PRESSURE": 382.4,
                "OWC": 1700.0,
                "PCOWC": 0.0,
                "GOC": 0.0,
                "PCGOC": 0.0,
                "INITRS": 1.0,
                "INITRV": 0.0,
                "OIP_INIT": 20.0,
                "EQLNUM": 1,
                "KEYWORD": "EQUIL",
            },
            {
                "Z": 2469.0,
                "PRESSURE": 382.4,
                "OWC": 1000.0,
                "PCOWC": 0.0,
                "GOC": 0.0,
                "PCGOC": 0.0,
                "INITRS": 2.0,
                "INITRV": 0.0,
                "OIP_INIT": 20.0,
                "EQLNUM": 2,
                "KEYWORD": "EQUIL",
            },
        ]
    )
    expected["RSVD"] = pd.DataFrame(
        [
            {"Z": 1500.0, "EQLNUM": 1, "KEYWORD": "RSVD", "RS": 184.0},
            {"Z": 4000.0, "EQLNUM": 1, "KEYWORD": "RSVD", "RS": 184.0},
            {"Z": 1500.0, "EQLNUM": 2, "KEYWORD": "RSVD", "RS": 184.0},
            {"Z": 4000.0, "EQLNUM": 2, "KEYWORD": "RSVD", "RS": 184.0},
        ]
    )

    for keyword, df in equildf.groupby("KEYWORD"):
        pd.testing.assert_frame_equal(
            df.dropna(axis=1).reset_index(drop=True), expected[keyword]
        )

    # Check that we can dump from dataframe to include file
    # and reparse to the same dataframe:
    inc = equil.df2ecl(equildf, withphases=True)
    df_from_inc = equil.df(inc)
    pd.testing.assert_frame_equal(equildf, df_from_inc, check_dtype=False)


def test_df2ecl(tmpdir):
    """Test that we can write include files to disk"""
    tmpdir.chdir()
    eclfiles = EclFiles(DATAFILE)
    equildf = equil.df(eclfiles)
    equil.df2ecl(equildf, filename="equil.inc")
    assert Path("equil.inc").is_file()

    # Test automatic directory creation:
    equil.df2ecl(equildf, filename="eclipse/include/equil.inc")
    assert Path("eclipse/include/equil.inc").is_file()


def test_decks():
    """Test some string decks"""
    deckstr = """
OIL
WATER
GAS

EQUIL
 2000 200 2200 /
"""
    df = equil.df(deckstr)
    assert df["OWC"].values == 2200
    assert len(df) == 1
    assert "IGNORE1" not in df
    assert df["EQLNUM"].unique()[0] == 1
    inc = equil.df2ecl(df, withphases=True)
    df_from_inc = equil.df(inc)
    # 0 columns can be both integers and floats.
    pd.testing.assert_frame_equal(df, df_from_inc, check_dtype=False)

    # Test empty data:
    inc = equil.df2ecl_equil(equil.df(""))
    assert "No data" in inc
    assert equil.df(inc).empty

    deckstr = """
OIL
WATER

EQUIL
 2000 200 2200 /
"""
    df = equil.df(deckstr)
    assert df["OWC"].values == 2200
    assert len(df) == 1
    assert "IGNORE1" not in df
    inc = equil.df2ecl(df, withphases=True)
    df_from_inc = equil.df(inc)
    # 0 columns can be both integers and floats.
    pd.testing.assert_frame_equal(df, df_from_inc, check_dtype=False)

    deckstr = """
GAS
WATER

EQUIL
 2000 200 2200 /
"""
    df = equil.df(deckstr)
    assert df["GWC"].values == 2200
    assert "OWC" not in df
    assert len(df) == 1
    assert "IGNORE2" not in df
    inc = equil.df2ecl(df, withphases=True)
    df_from_inc = equil.df(inc)
    # 0 columns can be both integers and floats.
    pd.testing.assert_frame_equal(df, df_from_inc, check_dtype=False)

    deckstr = """
GAS
OIL

EQUIL
 2000 200 2200 1 2100 3 /
"""
    df = equil.df(deckstr)
    assert df["GOC"].values == 2100
    assert "GWC" not in df
    assert "OWC" not in df
    assert len(df) == 1
    assert "IGNORE2" not in df
    inc = equil.df2ecl(df, withphases=True)
    df_from_inc = equil.df(inc)
    # 0 columns can be both integers and floats.
    pd.testing.assert_frame_equal(df, df_from_inc, check_dtype=False)

    deckstr = """
OIL
WATER
GAS

-- Output file printed by ecl2df.equil 0.5.2.dev12+g785dc0d.d20200402
-- at 2020-04-03 16:18:57.450100

EQUIL
--   DATUM  PRESSURE     OWC  PCOWC  GOC  PCGOC  INITRS  INITRV  ACCURACY
 2469.0     382.4  1700.0    0.0  0.0    0.0     1     0      20  /
 2469.0     382.4  1000.0    0.0  0.0    0.0     2     0      20  /
"""
    df = equil.df(deckstr)
    assert set(df["GOC"].values) == {0.0}
    assert "GWC" not in df
    assert "OWC" in df
    assert len(df) == 2
    assert "IGNORE2" not in df
    inc = equil.df2ecl(df, withphases=True)
    df_from_inc = equil.df(inc)
    # 0 columns can be both integers and floats.
    pd.testing.assert_frame_equal(df, df_from_inc, check_dtype=False)


def test_rsvd():
    """Test RSVD tables"""
    deckstr = """
RSVD
 10 100 /
 30 400 /
 50 100 /"""
    rsvd_df = equil.df(deckstr)
    assert "KEYWORD" in rsvd_df
    assert "EQUIL" not in rsvd_df["KEYWORD"].values
    assert max(rsvd_df["EQLNUM"]) == 3
    assert set(rsvd_df["Z"].values) == {10, 30, 50}
    assert set(rsvd_df["RS"].values) == {100, 400}
    inc = equil.df2ecl(rsvd_df)
    df_from_inc = equil.df(inc)
    pd.testing.assert_frame_equal(rsvd_df, df_from_inc)

    assert equil.df(deckstr, keywords="EQUIL").empty

    # Check that we can use the underlying function directly:
    rsvd_df2 = equil.rsvd_fromdeck(deckstr)
    pd.testing.assert_frame_equal(rsvd_df.drop("KEYWORD", axis="columns"), rsvd_df2)

    deckstr = """
RSVD
 10 100
 30 400 /
 50 100
 60 1000 /"""
    rsvd_df = equil.df(deckstr)
    assert "KEYWORD" in rsvd_df
    assert "EQUIL" not in rsvd_df["KEYWORD"].values
    assert len(rsvd_df) == 4
    assert max(rsvd_df["EQLNUM"]) == 2
    assert set(rsvd_df["Z"].values) == {10, 30, 50, 60}
    assert set(rsvd_df["RS"].values) == {100, 400, 1000}
    inc = equil.df2ecl(rsvd_df)
    df_from_inc = equil.df(inc)
    pd.testing.assert_frame_equal(rsvd_df, df_from_inc)

    # Check that we can use the underlying function directly:
    rsvd_df2 = equil.rsvd_fromdeck(deckstr)
    pd.testing.assert_frame_equal(rsvd_df.drop("KEYWORD", axis="columns"), rsvd_df2)


def test_rvvd():
    """Test RVVD tables"""
    deckstr = """
RVVD
 10 100 /
 30 400 /
 50 100 /"""
    rvvd_df = equil.df(deckstr)
    assert "KEYWORD" in rvvd_df
    assert "EQUIL" not in rvvd_df["KEYWORD"].values
    assert max(rvvd_df["EQLNUM"]) == 3
    assert set(rvvd_df["Z"].values) == {10, 30, 50}
    assert set(rvvd_df["RV"].values) == {100, 400}

    inc = equil.df2ecl(rvvd_df)
    df_from_inc = equil.df(inc)
    pd.testing.assert_frame_equal(rvvd_df, df_from_inc)

    assert equil.df(deckstr, keywords="EQUIL").empty

    # Check that we can use the underlying function directly:
    rvvd_df2 = equil.rvvd_fromdeck(deckstr)
    pd.testing.assert_frame_equal(rvvd_df.drop("KEYWORD", axis="columns"), rvvd_df2)

    deckstr = """
RVVD
 10 100
 30 400 /
 50 100
 60 1000 /"""
    rvvd_df = equil.df(deckstr)
    assert "KEYWORD" in rvvd_df
    assert "EQUIL" not in rvvd_df["KEYWORD"].values
    assert len(rvvd_df) == 4
    assert max(rvvd_df["EQLNUM"]) == 2
    assert set(rvvd_df["Z"].values) == {10, 30, 50, 60}
    assert set(rvvd_df["RV"].values) == {100, 400, 1000}

    inc = equil.df2ecl(rvvd_df)
    df_from_inc = equil.df(inc)
    pd.testing.assert_frame_equal(rvvd_df, df_from_inc)


def test_pbvd():
    """Test PBVD tables"""
    deckstr = """
PBVD
 10 100 /
 30 400 /
 50 100 /"""
    pbvd_df = equil.df(deckstr)
    assert "KEYWORD" in pbvd_df
    assert "EQUIL" not in pbvd_df["KEYWORD"].values
    assert max(pbvd_df["EQLNUM"]) == 3
    assert set(pbvd_df["Z"].values) == {10, 30, 50}
    assert set(pbvd_df["PB"].values) == {100, 400}

    inc = equil.df2ecl(pbvd_df)
    df_from_inc = equil.df(inc)
    pd.testing.assert_frame_equal(pbvd_df, df_from_inc)

    assert equil.df(deckstr, keywords="EQUIL").empty

    # Check that we can use the underlying function directly:
    pbvd_df2 = equil.pbvd_fromdeck(deckstr)
    pd.testing.assert_frame_equal(pbvd_df.drop("KEYWORD", axis="columns"), pbvd_df2)


def test_pdvd():
    """Test PDVD tables"""
    deckstr = """
PDVD
 10 100 /
 30 400 /
 50 100 /"""
    pdvd_df = equil.df(deckstr)
    assert "KEYWORD" in pdvd_df
    assert "EQUIL" not in pdvd_df["KEYWORD"].values
    assert max(pdvd_df["EQLNUM"]) == 3
    assert set(pdvd_df["Z"].values) == {10, 30, 50}
    assert set(pdvd_df["PD"].values) == {100, 400}

    inc = equil.df2ecl(pdvd_df)
    df_from_inc = equil.df(inc)
    pdvd_df2 = equil.pdvd_fromdeck(deckstr)
    pd.testing.assert_frame_equal(pdvd_df, df_from_inc)

    assert equil.df(deckstr, keywords="EQUIL").empty

    # Check that we can use the underlying function directly:
    pdvd_df2 = equil.pdvd_fromdeck(deckstr)
    pd.testing.assert_frame_equal(pdvd_df.drop("KEYWORD", axis="columns"), pdvd_df2)


def test_rsvd_via_file(tmpdir, mocker):
    """Test that we can reparse RSVD with unknown TABDIMS
    from a file using the command line utility"""
    tmpdir.chdir()
    deckstr = """
RSVD
 10 100
 30 400 /
 50 100
 60 1000 /"""
    rsvd_df = equil.df(deckstr)
    with open("rsvd.inc", "w") as filehandle:
        filehandle.write(deckstr)
    mocker.patch("sys.argv", ["ecl2csv", "equil", "-v", "rsvd.inc", "-o", "rsvd.csv"])
    ecl2csv.main()
    rsvd_df_fromcsv = pd.read_csv("rsvd.csv")
    pd.testing.assert_frame_equal(rsvd_df, rsvd_df_fromcsv)


def test_ntequl():
    """Test that we can infer NTEQUL when not supplied"""
    deckstr = """
GAS
OIL

EQUIL
 2000 200 2200 1 2100 3 /
 3000 200 2200 1 2100 3 /
"""
    df = equil.df(deckstr)
    assert set(df["GOC"].values) == set([2100, 2100])
    assert len(df) == 2
    assert df["EQLNUM"].min() == 1
    assert df["EQLNUM"].max() == 2
    # Supply correct NTEQUL instead of estimating
    df = equil.df(deckstr, ntequl=2)
    assert len(df) == 2

    inc = equil.df2ecl(df, withphases=True)
    df_from_inc = equil.df(inc)
    pd.testing.assert_frame_equal(df, df_from_inc, check_dtype=False)

    # Supplying wrong NTEQUIL:
    df = equil.df(deckstr, ntequl=1)
    # We are not able to catch this situation..
    assert len(df) == 1
    # But this will fail:
    with pytest.raises(ValueError):
        equil.df(deckstr, ntequl=3)

    deckstr = """
GAS
OIL

EQLDIMS
 2 /

EQUIL
 2000 200 2200 1 2100 3 /
 3000 200 2200 1 2100 3 /
"""
    df = equil.df(deckstr)
    assert set(df["GOC"].values) == set([2100, 2100])
    assert len(df) == 2

    inc = equil.df2ecl(df, withphases=True)
    df_from_inc = equil.df(inc)
    pd.testing.assert_frame_equal(df, df_from_inc, check_dtype=False)


@pytest.mark.parametrize(
    "somefloat, expected",
    [
        (1000.00000000000000000005, " 1000.0 "),
        (1000.0000000000003, " 1000.0 "),  # Many decimals may destabilize Eclipse
        (1000.0000003, " 1000.0 "),
        (1000.000003, " 1000.000003 "),  # Assume Eclipse accepts this
        (np.float32(1000.00003), " 1000.0 "),
        (np.float32(1000.0003), " 1000.0003"),  # can give 1000.000305
    ],
)
def test_eclipse_rounding(somefloat, expected):
    """Values in include files with a lot of decimals, like you sometimes get
    from Python floating point operations may crash Eclipse. Ensure these are
    rounded (the typical output routine is pd.DataFrame.to_string())

    As an example, 1000.00000000000000000005 as a datum value in EQUIL has been
    observed to crash Eclipse. It would be hard to get Python to output this
    particular value.
    """

    dframe = pd.DataFrame(
        [
            {
                "Z": 2469.0,
                "PRESSURE": 382.4,
                "OWC": somefloat,
                "PCOWC": 0.0,
                "GOC": 0.0,
                "PCGOC": 0.0,
                "INITRS": 1.0,
                "INITRV": 0.0,
                "EQLNUM": 1,
                "KEYWORD": "EQUIL",
            }
        ]
    )
    assert expected in equil.df2ecl(dframe, withphases=False)


def test_main_subparser(tmpdir, mocker):
    """Test command line interface"""
    tmpdir.chdir()
    tmpcsvfile = "equil.csv"
    mocker.patch("sys.argv", ["ecl2csv", "equil", "-v", DATAFILE, "-o", tmpcsvfile])
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty

    # Test the reverse operation:
    mocker.patch(
        "sys.argv", ["csv2ecl", "equil", "-v", "--output", "equil.inc", tmpcsvfile]
    )
    csv2ecl.main()
    # NB: cvs2ecl does not output the phase configuration!
    phases = "WATER\nGAS\nOIL\n\n"
    ph_equil_inc = Path("phasesequil.inc")
    ph_equil_inc.write_text(phases + Path("equil.inc").read_text())

    pd.testing.assert_frame_equal(equil.df(ph_equil_inc.read_text()), disk_df)

    # Test via stdout:
    result = subprocess.run(
        ["csv2ecl", "equil", "--output", "-", tmpcsvfile],
        stdout=subprocess.PIPE,
    )
    pd.testing.assert_frame_equal(
        equil.df(phases + result.stdout.decode()),
        disk_df,
        check_like=True,
    )
