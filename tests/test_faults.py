"""Test module for nnc2df"""

import io
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from res2df import faults, res2csv
from res2df.resdatafiles import ResdataFiles

try:
    # pylint: disable=unused-import
    import opm  # noqa
except ImportError:
    pytest.skip(
        "OPM is not installed, nothing relevant in here then",
        allow_module_level=True,
    )

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS")


def test_faults2df():
    """Test that dataframes are produced"""
    resdatafiles = ResdataFiles(REEK)
    faultsdf = faults.df(resdatafiles.get_deck())

    assert "NAME" in faultsdf
    assert "I" in faultsdf
    assert "J" in faultsdf
    assert "K" in faultsdf
    assert "FACE" in faultsdf

    assert not faultsdf.empty


def test_str2df():
    """Test making dataframe from a string"""
    deckstr = """
FAULTS
  'A' 1 2 3 4 5 6 'I' /
  'B' 2 3 4 5 6 7 'J' /
/
"""
    deck = ResdataFiles.str2deck(deckstr)
    faultsdf = faults.df(deck)

    assert len(faultsdf) == 16


def test_nofaults():
    """Test on a dataset with no faults"""
    resdatafiles = ResdataFiles(EIGHTCELLS)
    faultsdf = faults.df(resdatafiles.get_deck())
    assert faultsdf.empty


def test_multiplestr2df():
    """Test that we support multiple occurences of the FAULTS keyword"""
    deckstr = """
FAULTS
  'A' 1 2 3 4 5 6 'I' /
  'B' 2 3 4 5 6 7 'J' /
/
FAULTS
  'C' 1 1 3 3 10 15 'I' /
  'D' 2 2 4 4 10 10 'J' /
/
"""
    deck = ResdataFiles.str2deck(deckstr)
    faultsdf = faults.df(deck).set_index("NAME")

    assert len(faultsdf) == 23
    assert len(faultsdf.loc[["D"]]) == 1  # Pass lists to .loc for single row
    assert len(faultsdf.loc["C"]) == 6


def test_main_subparser(tmp_path, mocker):
    """Test command line interface with subparsers"""
    tmpcsvfile = tmp_path / "faultsdf.csv"
    mocker.patch("sys.argv", ["res2csv", "faults", REEK, "-o", str(tmpcsvfile)])
    res2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty


def test_magic_stdout():
    """Test that we can pipe the output into a dataframe"""
    result = subprocess.run(
        ["res2csv", "faults", "-o", "-", REEK], check=True, stdout=subprocess.PIPE
    )
    df_stdout = pd.read_csv(io.StringIO(result.stdout.decode()))
    assert not df_stdout.empty
