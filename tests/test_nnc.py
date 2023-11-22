"""Test module for nnc2df"""

import io
import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from res2df import faults, nnc, res2csv, trans
from res2df.resdatafiles import ResdataFiles

try:
    # pylint: disable=unused-import
    import opm  # noqa

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False


TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")


def test_nnc2df():
    """Test that dataframes are produced"""
    resdatafiles = ResdataFiles(REEK)
    nncdf = nnc.df(resdatafiles)

    assert not nncdf.empty
    assert "I1" in nncdf
    assert "J1" in nncdf
    assert "K1" in nncdf
    assert "I2" in nncdf
    assert "J2" in nncdf
    assert "K2" in nncdf
    assert "TRAN" in nncdf

    prelen = len(nncdf)
    nncdf = nnc.filter_vertical(nncdf)
    assert (nncdf["I1"] == nncdf["I2"]).all()
    assert (nncdf["J1"] == nncdf["J2"]).all()
    assert len(nncdf) < prelen


def test_no_nnc():
    """Test nnc on an Eclipse case with no NNCs"""
    resdatafiles = ResdataFiles(EIGHTCELLS)
    assert nnc.df(resdatafiles).empty


def test_nnc2df_coords():
    """Test that we are able to add coordinates"""
    resdatafiles = ResdataFiles(REEK)
    gnncdf = nnc.df(resdatafiles, coords=True)
    assert not gnncdf.empty
    assert "X" in gnncdf
    assert "Y" in gnncdf
    assert "Z" in gnncdf


@pytest.mark.skipif(not HAVE_OPM, reason="Requires OPM")
def test_nnc2df_faultnames():
    """Add faultnames from FAULTS keyword to connections"""
    resdatafiles = ResdataFiles(REEK)
    nncdf = nnc.df(resdatafiles)
    faultsdf = faults.df(resdatafiles.get_deck())

    merged = pd.merge(
        nncdf,
        faultsdf,
        how="left",
        left_on=["I1", "J1", "K1"],
        right_on=["I", "J", "K"],
    )
    merged = pd.merge(
        merged,
        faultsdf,
        how="left",
        left_on=["I2", "J2", "K2"],
        right_on=["I", "J", "K"],
    )
    # Fix columnnames so that we don't get FACE_x and FACE_y etc.
    # Remove I_x, J_x, K_x (and _y) which is not needed


def test_df2res_editnnc(tmp_path):
    """Test generation of EDITNNC keyword"""
    resdatafiles = ResdataFiles(REEK)
    nncdf = nnc.df(resdatafiles)
    os.chdir(tmp_path)

    nncdf["TRANM"] = 2
    editnnc = nnc.df2res_editnnc(nncdf, filename="editnnc.inc")
    editnnc_fromfile = Path("editnnc.inc").read_text(encoding="utf8")
    assert editnnc == editnnc_fromfile
    assert "EDITNNC" in editnnc
    assert editnnc.count("/") == len(nncdf) + 1
    assert "avg multiplier" in editnnc

    # Fails when columns are missing
    with pytest.raises((KeyError, ValueError)):
        nnc.df2res_editnnc(nncdf[["I1", "I2"]])

    editnnc = nnc.df2res_editnnc(nncdf, nocomments=True)
    assert "avg multiplier" not in editnnc

    # Test compatibility with trans module:
    trans_df = trans.df(resdatafiles, addnnc=True)
    editnnc = nnc.df2res_editnnc(trans_df.assign(TRANM=0.3))
    assert "avg multiplier 0.3" in editnnc or "avg multiplier 0.29999" in editnnc

    print(nnc.df2res_editnnc(nnc.df(resdatafiles).head(4).assign(TRANM=0.1)))


@pytest.mark.skipif(not HAVE_OPM, reason="Requires OPM")
def test_main(tmp_path, mocker):
    """Test command line interface"""
    tmpcsvfile = tmp_path / "nnc.csv"
    mocker.patch("sys.argv", ["res2csv", "nnc", "-v", REEK, "-o", str(tmpcsvfile)])
    res2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
    assert "I1" in disk_df
    assert "TRAN" in disk_df


@pytest.mark.skipif(not HAVE_OPM, reason="Requires OPM")
def test_magic_stdout():
    """Test that we can pipe the output into a dataframe"""
    result = subprocess.run(
        ["res2csv", "nnc", "-o", "-", REEK], check=True, stdout=subprocess.PIPE
    )
    df_stdout = pd.read_csv(io.StringIO(result.stdout.decode()))
    assert not df_stdout.empty
