"""Test module for pvt"""

import sys
from pathlib import Path

import logging
import pandas as pd

import pytest

from ecl2df import pvt, ecl2csv, csv2ecl
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")

logger = logging.getLogger("")
logger.setLevel(logging.DEBUG)


def test_pvto_strings():
    """Test PVTO parsing from strings"""
    pvto_deck = """PVTO
    0      1 1.0001 1
         200 1.000  1.001 /
    18    25 1.14  0.59 /
    /  -- One table (pvtnum=1), two records (two gor's)
    """
    dframe = pvt.pvto_fromdeck(EclFiles.str2deck(pvto_deck))
    assert "PVTNUM" in dframe
    assert "RS" in dframe
    assert "PRESSURE" in dframe
    assert "VISCOSITY" in dframe
    assert "VOLUMEFACTOR" in dframe
    assert len(dframe) == 3
    assert len(dframe["RS"].unique()) == 2
    assert len(dframe["PRESSURE"].unique()) == 3
    assert len(dframe["VOLUMEFACTOR"].unique()) == 3
    assert len(dframe["VISCOSITY"].unique()) == 3
    assert set(dframe["PVTNUM"].values) == {1}
    assert max(dframe["PRESSURE"]) == 200

    dframe_via_string = pvt.pvto_fromdeck(pvt.df2ecl_pvto(dframe))
    pd.testing.assert_frame_equal(dframe_via_string, dframe)

    # Provide TABDIMS in first test.. Infer later
    pvto_deck = """TABDIMS
     1 2 /

    PVTO
    0      1 1.0001 1
         200 1.000  1.001 /
    18    25 1.14  0.59 /
    /
    1      2 1.0001 1
         333 1.000  1.001 /
    19    30 1.14  0.59 /
    /
    """
    dframe = pvt.pvto_fromdeck(EclFiles.str2deck(pvto_deck))
    assert len(dframe) == 6
    assert "PVTNUM" in dframe
    assert set(dframe["PVTNUM"].astype(int).unique()) == {1, 2}
    assert len(dframe["RS"].unique()) == 4
    assert len(dframe["PRESSURE"].unique()) == 6
    assert len(dframe["VOLUMEFACTOR"].unique()) == 3

    dframe_via_string = pvt.pvto_fromdeck(pvt.df2ecl_pvto(dframe))
    pd.testing.assert_frame_equal(dframe_via_string, dframe)

    # Now test the same but without TABDIMS:
    pvto_deck = """
    PVTO
    0      1 1.0001 1
         200 1.000  1.001 /
    18    25 1.14  0.59 /
    /
    1      2 1.0001 1
         333 1.000  1.001 /
    19    30 1.14  0.59 /
    /
    """
    dframe = pvt.pvto_fromdeck(pvto_deck)
    assert len(dframe) == 6
    assert "PVTNUM" in dframe
    assert set(dframe["PVTNUM"].astype(int).unique()) == {1, 2}
    assert len(dframe["RS"].unique()) == 4
    assert len(dframe["PRESSURE"].unique()) == 6
    assert len(dframe["VOLUMEFACTOR"].unique()) == 3
    dframe_via_string = pvt.pvto_fromdeck(pvt.df2ecl_pvto(dframe))
    pd.testing.assert_frame_equal(dframe_via_string, dframe)

    # Test emtpy data:
    inc = pvt.df2ecl_pvto(pvt.df(""))
    assert "No data" in inc
    assert pvt.df(inc).empty


def test_pvdg_string():
    """Test that PVDG can be parsed from a string"""
    string = """
PVDG
400 6 0.01
600 3 0.012
1000 1.3 0.15 /
200 8 0.013
300 4 0.014
8000 1.8 0.16 /
"""
    dframe = pvt.pvdg_fromdeck(string)
    assert len(dframe) == 6
    assert "PVTNUM" in dframe
    assert len(dframe["PVTNUM"].unique()) == 2
    assert "PRESSURE" in dframe
    assert "VOLUMEFACTOR" in dframe
    assert "VISCOSITY" in dframe

    # Test emtpy data:
    inc = pvt.df2ecl_pvdg(pvt.df(""))
    assert "No data" in inc
    assert pvt.df(inc).empty


def test_pvdo_string():
    """Test that PVDO can be parsed from a string"""
    string = """
PVDO
400 6 0.01
600 3 0.012
1000 1.3 0.15 /
200 8 0.013
300 4 0.014
8000 1.8 0.16 /
"""
    dframe = pvt.pvdo_fromdeck(string)
    assert len(dframe) == 6
    assert "PVTNUM" in dframe
    assert len(dframe["PVTNUM"].unique()) == 2
    assert "PRESSURE" in dframe
    assert "VOLUMEFACTOR" in dframe
    assert "VISCOSITY" in dframe

    # Test emtpy data:
    inc = pvt.df2ecl_pvdo(pvt.df(""))
    assert "No data" in inc
    assert pvt.df(inc).empty


def test_pvt_reek():
    """Test that the Reek PVT input can be parsed individually"""

    eclfiles = EclFiles(DATAFILE)
    pvto_df = pvt.pvto_fromdeck(eclfiles.get_ecldeck())
    assert "PVTNUM" in pvto_df
    assert "PRESSURE" in pvto_df
    assert "VOLUMEFACTOR" in pvto_df
    assert "VISCOSITY" in pvto_df
    assert max(pvto_df["PVTNUM"]) == 1
    assert max(pvto_df["PRESSURE"]) == 700.1
    # Check count of undersaturated lines pr. RS:
    # (nb: double brackets in .loc to ensure dataframe is returned)
    assert len(pvto_df.set_index("RS").loc[[0]]) == 2
    assert len(pvto_df.set_index("RS").loc[[15.906]]) == 1
    assert len(pvto_df.set_index("RS").loc[[105.5]]) == 15
    assert len(pvto_df["RS"].unique()) == 20
    assert pvto_df["VOLUMEFACTOR"].max() == 2.851
    assert pvto_df["VISCOSITY"].max() == 1.0001

    dframe_via_string = pvt.pvto_fromdeck(pvt.df2ecl_pvto(pvto_df))
    pd.testing.assert_frame_equal(dframe_via_string, pvto_df)

    density_df = pvt.density_fromdeck(eclfiles.get_ecldeck())
    assert "PVTNUM" in density_df
    assert "OILDENSITY" in density_df
    assert "WATERDENSITY" in density_df
    assert "GASDENSITY" in density_df
    assert len(density_df) == 1
    assert density_df["WATERDENSITY"].values[0] == 999.04
    dframe_via_string = pvt.density_fromdeck(pvt.df2ecl_density(density_df))
    pd.testing.assert_frame_equal(dframe_via_string, density_df)

    rock_df = pvt.rock_fromdeck(eclfiles.get_ecldeck())
    assert "PVTNUM" in rock_df
    assert len(rock_df) == 1
    assert "PRESSURE" in rock_df
    assert "COMPRESSIBILITY" in rock_df
    assert rock_df["PRESSURE"].values[0] == 327.3

    pvtw_df = pvt.pvtw_fromdeck(eclfiles.get_ecldeck())
    assert "PVTNUM" in pvtw_df
    assert pvtw_df["PVTNUM"].values[0] == 1
    assert len(pvtw_df) == 1
    assert "PRESSURE" in pvtw_df
    assert "VOLUMEFACTOR" in pvtw_df
    assert "COMPRESSIBILITY" in pvtw_df
    assert "VISCOSITY" in pvtw_df
    assert "VISCOSIBILITY" in pvtw_df
    assert pvtw_df["VISCOSITY"].values[0] == 0.25

    pvdg_df = pvt.pvdg_fromdeck(eclfiles.get_ecldeck())
    assert "PVTNUM" in pvdg_df
    assert "PRESSURE" in pvdg_df
    assert "VOLUMEFACTOR" in pvdg_df
    assert "VISCOSITY" in pvdg_df
    assert len(pvdg_df["PVTNUM"].unique()) == 1
    assert pvdg_df["PVTNUM"].max() == 1
    assert len(pvdg_df) == 15


def test_pvtg_string():
    """Test parsing of PVTG"""

    # Example data from E100 manual
    string = """
PVTG
30 0.00014    0.0523 0.0234
   0          0.0521 0.0238 /
90 0.00012    0.0132 0.0252
   0          0.0131 0.0253 /
150 0.00015   0.00877 0.0281
   0          0.00861 0.0275 /
210 0.00019   0.00554 0.0318
    0         0.00555 0.0302 /
270 0.00029   0.00417 0.0355
    0         0.00421 0.0330 /
330 0.00049   0.00357 0.0392
    0         0.00361 0.0358 /
530 0.00060   0.00356 0.0393
    0         0.00360 0.0359 /
/ null record to terminate table 1
60 0.00014    0.0523 0.0234 /
120 0.00012   0.0132 0.0252 /
180 0.00015   0.00877 0.0281 /
240 0.00019   0.00554 0.0318 /
300 0.00029   0.00417 0.0355 /
360 0.00049   0.00357 0.0392 /
560 0.00060   0.00356 0.0393
    0         0.00360 0.0359 / undersaturated data for Pg=560
/ null record to terminate table 2
"""
    pvtg_df = pvt.pvtg_fromdeck(string)
    assert "PRESSURE" in pvtg_df
    assert "OGR" in pvtg_df
    assert "PVTNUM" in pvtg_df
    assert "VOLUMEFACTOR" in pvtg_df
    assert "VISCOSITY" in pvtg_df
    assert len(pvtg_df["PVTNUM"].unique()) == 2
    assert len(pvtg_df["PRESSURE"].unique()) == 14
    assert max(pvtg_df["VOLUMEFACTOR"]) == 0.0523
    assert max(pvtg_df["VISCOSITY"]) == 0.0393

    # Test emtpy data:
    inc = pvt.df2ecl_pvtg(pvt.df(""))
    assert "No data" in inc
    assert pvt.df(inc).empty


def test_density():
    """Test that DENSITY can be parsed from files and from strings"""
    eclfiles = EclFiles(DATAFILE)
    density_df = pvt.density_fromdeck(eclfiles.get_ecldeck())
    assert len(density_df) == 1
    assert "PVTNUM" in density_df
    assert "OILDENSITY" in density_df
    assert "WATERDENSITY" in density_df
    assert "GASDENSITY" in density_df

    dframe_via_string = pvt.density_fromdeck(pvt.df2ecl_density(density_df))
    pd.testing.assert_frame_equal(dframe_via_string, density_df)

    two_pvtnum_deck = """DENSITY
        860      999.04       1.1427 /
        800      950     1.05
        /
        """
    density_df = pvt.density_fromdeck(EclFiles.str2deck(two_pvtnum_deck))
    # (a warning will be printed that we cannot guess)
    assert len(density_df) == 1
    density_df = pvt.density_fromdeck(two_pvtnum_deck)
    assert "PVTNUM" in density_df
    assert density_df["PVTNUM"].max() == 2
    assert density_df["PVTNUM"].min() == 1
    assert "OILDENSITY" in density_df
    dframe_via_string = pvt.density_fromdeck(pvt.df2ecl_density(density_df))
    pd.testing.assert_frame_equal(dframe_via_string, density_df)

    # Test emtpy data:
    inc = pvt.df2ecl_density(pvt.df(""))
    assert "No data" in inc
    assert pvt.df(inc).empty


def test_pvtw():
    """Test that PVTW can be parsed from a string"""
    deck = """PVTW
     327.3         1.03    4.51E-005         0.25            0 /"""
    pvtw_df = pvt.pvtw_fromdeck(EclFiles.str2deck(deck))
    assert len(pvtw_df) == 1
    assert "VOLUMEFACTOR" in pvtw_df
    assert "PRESSURE" in pvtw_df
    assert "COMPRESSIBILITY" in pvtw_df
    assert "VISCOSIBILITY" in pvtw_df

    deck = """PVTW
     327.3         1.03    4.51E-005         0.25            0 /
     300           1    0.0001  0.2 /"""
    pvtw_df = pvt.pvtw_fromdeck(deck)  # Must give string, not deck, for NTPVT guessing
    assert len(pvtw_df) == 2

    # Test emtpy data:
    inc = pvt.df2ecl_pvtw(pvt.df(""))
    assert "No data" in inc
    assert pvt.df(inc).empty


def test_rock():
    """Test parsing of the ROCK keyword from a string"""
    deck = """ROCK
     100 1.1 /"""
    rock_df = pvt.rock_fromdeck(EclFiles.str2deck(deck))
    assert len(rock_df) == 1
    assert "PRESSURE" in rock_df
    assert "COMPRESSIBILITY" in rock_df
    dframe_via_string = pvt.rock_fromdeck(pvt.df2ecl_rock(rock_df))
    pd.testing.assert_frame_equal(dframe_via_string, rock_df)

    # Test emtpy data:
    inc = pvt.df2ecl_rock(pvt.df(""))
    assert "No data" in inc
    assert pvt.df(inc).empty


def test_df():
    """Test that aggregate dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)  # Reek dataset
    pvtdf = pvt.df(eclfiles)

    assert not pvtdf.empty
    assert set(pvtdf["KEYWORD"]) == {"PVTO", "PVDG", "DENSITY", "ROCK", "PVTW"}
    assert "PVTNUM" in pvtdf
    assert "PRESSURE" in pvtdf
    assert "RS" in pvtdf
    assert "COMPRESSIBILITY" in pvtdf
    assert "VISCOSITY" in pvtdf
    assert len(pvtdf["PVTNUM"].unique()) == 1


def test_main(tmpdir):
    """Test command line interface"""
    tmpcsvfile = str(tmpdir.join("pvt.csv"))
    sys.argv = ["ecl2csv", "pvt", "-v", DATAFILE, "-o", tmpcsvfile]
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(tmpcsvfile)
    assert "PVTNUM" in disk_df
    assert "KEYWORD" in disk_df
    assert not disk_df.empty

    # Write back to include file:
    incfile = str(tmpdir.join("pvt.inc"))
    sys.argv = ["csv2ecl", "pvt", "-v", str(tmpcsvfile), "-o", incfile]
    csv2ecl.main()

    # Reparse the include file on disk back to dataframe
    # and check dataframe equality
    assert Path(incfile).is_file()
    disk_inc_df = pvt.df(open(incfile).read())
    pd.testing.assert_frame_equal(disk_df, disk_inc_df)


def test_df2ecl_pvto():
    """Test that we can print a PVTO dataframe to E100 include file"""
    dframe = pd.DataFrame(
        columns=["PVTNUM", "RS", "PRESSURE", "VOLUMEFACTOR", "VISCOSITY"],
        data=[[1, 50, 100, 2, 1.04]],
    )
    pvto_string = pvt.df2ecl_pvto(dframe)
    assert "PVTO" in pvto_string
    assert "1.04" in pvto_string
    assert "100" in pvto_string
    dframe_from_str = pvt.df(pvto_string)
    print(dframe_from_str)
    print(dframe)
    pd.testing.assert_frame_equal(
        dframe,
        dframe_from_str.drop("KEYWORD", axis="columns"),
        check_like=True,
        check_dtype=False,
    )

    dframe = pd.DataFrame(
        columns=["PVTNUM", "RS", "PRESSURE", "VOLUMEFACTOR", "VISCOSITY"],
        data=[[1, 50, 100, 2, 1.04], [1, 50, 120, 3, 1.05]],
    )
    pvto_string = pvt.df2ecl_pvto(dframe)
    assert "PVTO" in pvto_string
    assert "1.05" in pvto_string
    assert "120" in pvto_string
    dframe_from_str = pvt.df(pvto_string)
    pd.testing.assert_frame_equal(
        dframe,
        dframe_from_str.drop("KEYWORD", axis="columns"),
        check_like=True,
        check_dtype=False,
    )


def test_df2ecl(tmpdir):
    """Test generation of PVT include files from dataframes

    The validity of produced dataframes is tested in other test functions
    herein, here we mainly test for the API and error handling"""
    tmpdir.chdir()
    with pytest.raises(ValueError):
        pvt.df2ecl(pd.DataFrame())

    rock_df = pd.DataFrame(
        columns=["PVTNUM", "KEYWORD", "PRESSURE", "COMPRESSIBILITY"],
        data=[[1, "ROCK", 100, 0.001]],
    )

    rock_inc = pvt.df2ecl(rock_df)
    assert "ROCK" in rock_inc
    rock_inc = pvt.df2ecl(rock_df, comments=dict(ROCK="foo"))
    assert "foo" in rock_inc
    rock_inc = pvt.df2ecl(rock_df, comments=dict(DENSITY="foo"))
    assert "foo" not in rock_inc

    rock_inc = pvt.df2ecl(rock_df, comments=dict(ROCK="foo\nbar"), filename="foo.inc")
    assert Path("foo.inc").is_file()
    assert "foo" in rock_inc
    assert "bar" in rock_inc
    # Multiline comments are tricky, is the output valid?
    rock_df_from_inc = pvt.rock_fromdeck(rock_inc).assign(KEYWORD="ROCK")
    # Need to sort columns for comparison, as column order does not matter
    # in dataframes, but it does in the function assert_frame_equal
    rock_df_from_inc = rock_df_from_inc.reindex(
        sorted(rock_df_from_inc.columns), axis=1
    )
    rock_df = rock_df_from_inc.reindex(sorted(rock_df.columns), axis=1)
    print(rock_df_from_inc)
    print(rock_df)
    pd.testing.assert_frame_equal(rock_df_from_inc, rock_df)

    rock_inc = pvt.df2ecl(rock_df, keywords=["DENSITY"])
    assert not rock_inc
    rock_inc = pvt.df2ecl(rock_df, keywords="DENSITY")
    assert not rock_inc

    rock_inc = pvt.df2ecl(rock_df, keywords=["ROCK", "DENSITY"])
    assert "ROCK" in rock_inc
    assert "DENSITY" not in rock_inc
    rock_inc = pvt.df2ecl(rock_df, keywords="ROCK")
    assert "ROCK" in rock_inc
