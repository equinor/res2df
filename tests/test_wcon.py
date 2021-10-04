"""Test module for wcon"""

import io
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from ecl2df import ecl2csv, wcon
from ecl2df.eclfiles import EclFiles

try:
    import opm  # noqa
except ImportError:
    pytest.skip(
        "OPM is not installed",
        allow_module_level=True,
    )
TESTDIR = Path(__file__).absolute().parent
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")


def test_wcon2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(EIGHTCELLS)
    wcondf = wcon.df(eclfiles.get_ecldeck())

    assert not wcondf.empty
    assert "DATE" in wcondf  # for all data
    assert "KEYWORD" in wcondf
    for col in wcondf.columns:
        assert col == col.upper()


def test_wconhist():
    """Test WCONHIST parsing and column names"""
    wconstr = """
WCONHIST
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wconhist_df = wcon.df(deck)
    pd.testing.assert_frame_equal(
        wconhist_df,
        pd.DataFrame(
            [
                {
                    "WELL": "FOO",
                    "STATUS": "0",
                    "CMODE": "1",
                    "ORAT": 0,
                    "WRAT": 0,
                    "GRAT": 0,
                    "VFP_TABLE": 0,
                    "ALQ": 0,
                    "THP": 0,
                    "BHP": 0,
                    "NGLRAT": 0,
                    "DATE": None,
                    "KEYWORD": "WCONHIST",
                }
            ]
        ),
    )


def test_wconinjh():
    """Test WCONINJH parsing and column names"""
    wconstr = """
WCONINJH
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wconinjh_df = wcon.df(deck)
    pd.testing.assert_frame_equal(
        wconinjh_df,
        pd.DataFrame(
            [
                {
                    "WELL": "FOO",
                    "TYPE": "0",
                    "STATUS": "1",
                    "RATE": None,
                    "BHP": None,
                    "THP": None,
                    "VFP_TABLE": 0,
                    "VAPOIL_C": 0,
                    "SURFACE_OIL_FRACTION": 0,
                    "SURFACE_WATER_FRACTION": 0,
                    "SURFACE_GAS_FRACTION": 0,
                    "CMODE": "RATE",
                    "DATE": None,
                    "KEYWORD": "WCONINJH",
                }
            ]
        ),
    )


def test_wconinje():
    """Test WCONINJE parsing and column names"""
    wconstr = """
WCONINJE
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wconinje_df = wcon.df(deck)
    pd.testing.assert_frame_equal(
        wconinje_df,
        pd.DataFrame(
            [
                {
                    "WELL": "FOO",
                    "TYPE": "0",
                    "STATUS": "1",
                    "CMODE": None,
                    "RATE": None,
                    "RESV": None,
                    "BHP": 6895,
                    "THP": None,
                    "VFP_TABLE": 0,
                    "VAPOIL_C": 0,
                    "GAS_STEAM_RATIO": 0,
                    "SURFACE_OIL_FRACTION": 0,
                    "SURFACE_WATER_FRACTION": 0,
                    "SURFACE_GAS_FRACTION": 0,
                    "OIL_STEAM_RATIO": 0,
                    "DATE": None,
                    "KEYWORD": "WCONINJE",
                }
            ]
        ),
    )


def test_wconprod():
    """Test WCONPROD parsing and column names"""
    wconstr = """
WCONPROD
  'FOO' 0 1 /
 /
"""
    deck = EclFiles.str2deck(wconstr)
    wconprod_df = wcon.df(deck)
    pd.testing.assert_frame_equal(
        wconprod_df,
        pd.DataFrame(
            [
                {
                    "WELL": "FOO",
                    "STATUS": "0",
                    "CMODE": "1",
                    "ORAT": 0,
                    "WRAT": 0,
                    "GRAT": 0,
                    "LRAT": 0,
                    "RESV": 0,
                    "BHP": 1.01325,
                    "THP": 0,
                    "VFP_TABLE": 0,
                    "ALQ": 0,
                    # These E300 columns should not
                    # be regarded critical for API.
                    "E300_ITEM13": None,
                    "E300_ITEM14": None,
                    "E300_ITEM15": None,
                    "E300_ITEM16": None,
                    "E300_ITEM17": None,
                    "E300_ITEM18": None,
                    "E300_ITEM19": None,
                    "E300_ITEM20": None,
                    "DATE": None,
                    "KEYWORD": "WCONPROD",
                }
            ]
        ),
    )


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


def test_main_subparsers(tmp_path, mocker):
    """Test command line interface"""
    tmpcsvfile = tmp_path / ".TMP-wcondf.csv"
    mocker.patch("sys.argv", ["ecl2csv", "wcon", EIGHTCELLS, "-o", str(tmpcsvfile)])
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty


def test_magic_stdout():
    """Test that we can pipe the output into a dataframe"""
    result = subprocess.run(
        ["ecl2csv", "wcon", "-v", "-o", "-", EIGHTCELLS],
        check=True,
        stdout=subprocess.PIPE,
    )
    df_stdout = pd.read_csv(io.StringIO(result.stdout.decode()))
    assert not df_stdout.empty
