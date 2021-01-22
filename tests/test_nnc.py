"""Test module for nnc2df"""

import io
from pathlib import Path
import subprocess

import pandas as pd
import pytest

from ecl2df import nnc, faults, trans, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_nnc2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    nncdf = nnc.df(eclfiles)

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


def test_nnc2df_coords():
    """Test that we are able to add coordinates"""
    eclfiles = EclFiles(DATAFILE)
    gnncdf = nnc.df(eclfiles, coords=True)
    assert not gnncdf.empty
    assert "X" in gnncdf
    assert "Y" in gnncdf
    assert "Z" in gnncdf


def test_nnc2df_faultnames():
    """Add faultnames from FAULTS keyword to connections"""
    eclfiles = EclFiles(DATAFILE)
    nncdf = nnc.df(eclfiles)
    faultsdf = faults.df(eclfiles.get_ecldeck())

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


def test_df2ecl_editnnc(tmpdir):
    """Test generation of EDITNNC keyword"""
    eclfiles = EclFiles(DATAFILE)
    nncdf = nnc.df(eclfiles)
    tmpdir.chdir()

    nncdf["TRANM"] = 2
    editnnc = nnc.df2ecl_editnnc(nncdf, filename="editnnc.inc")
    editnnc_fromfile = "".join(open("editnnc.inc").readlines())
    assert editnnc == editnnc_fromfile
    assert "EDITNNC" in editnnc
    assert editnnc.count("/") == len(nncdf) + 1
    assert "avg multiplier" in editnnc

    # Fails when columns are missing
    with pytest.raises((KeyError, ValueError)):
        nnc.df2ecl_editnnc(nncdf[["I1", "I2"]])

    editnnc = nnc.df2ecl_editnnc(nncdf, nocomments=True)
    assert "avg multiplier" not in editnnc

    # Test compatibility with trans module:
    trans_df = trans.df(eclfiles, addnnc=True)
    editnnc = nnc.df2ecl_editnnc(trans_df.assign(TRANM=0.3))
    assert "avg multiplier 0.3" in editnnc or "avg multiplier 0.29999" in editnnc

    print(nnc.df2ecl_editnnc(nnc.df(eclfiles).head(4).assign(TRANM=0.1)))


def test_main(tmpdir, mocker):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join("nnc.csv")
    mocker.patch("sys.argv", ["ecl2csv", "nnc", "-v", DATAFILE, "-o", str(tmpcsvfile)])
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
    assert "I1" in disk_df
    assert "TRAN" in disk_df


def test_magic_stdout():
    """Test that we can pipe the output into a dataframe"""
    result = subprocess.run(
        ["ecl2csv", "nnc", "-o", "-", DATAFILE], check=True, stdout=subprocess.PIPE
    )
    df_stdout = pd.read_csv(io.StringIO(result.stdout.decode()))
    assert not df_stdout.empty
