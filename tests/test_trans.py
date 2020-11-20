"""Test module for ecl2df.trans"""

import sys
from pathlib import Path

import pandas as pd
import networkx

from ecl2df import trans
from ecl2df import ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_trans():
    """Test that we can build a dataframe of transmissibilities"""
    eclfiles = EclFiles(DATAFILE)
    trans_df = trans.df(eclfiles)
    assert "TRAN" in trans_df
    assert "DIR" in trans_df
    assert set(trans_df["DIR"].unique()) == set(["I", "J", "K"])
    assert trans_df["TRAN"].sum() > 0

    trans_full_length = len(trans_df)

    # Try including some vectors:
    trans_df = trans.df(eclfiles, vectors="FIPNUM")
    assert "FIPNUM" not in trans_df
    assert "FIPNUM1" in trans_df
    assert "EQLNUM2" not in trans_df

    trans_df = trans.df(eclfiles, vectors=["FIPNUM", "EQLNUM"])
    assert "FIPNUM1" in trans_df
    assert "EQLNUM2" in trans_df

    trans_df = trans.df(eclfiles, vectors="BOGUS")
    assert "BOGUS1" not in trans_df
    assert "TRAN" in trans_df  # (we should have gotten a warning only)

    assert "K" not in trans.df(eclfiles, onlyijdir=True)["DIR"]
    assert "I" not in trans.df(eclfiles, onlykdir=True)["DIR"]

    transnnc_df = trans.df(eclfiles, addnnc=True)
    assert len(transnnc_df) > trans_full_length

    trans_df = trans.df(eclfiles, vectors=["FIPNUM", "EQLNUM"], boundaryfilter=True)
    assert trans_df.empty

    trans_df = trans.df(eclfiles, vectors="FIPNUM", boundaryfilter=True)
    assert len(trans_df) < trans_full_length

    trans_df = trans.df(eclfiles, coords=True)
    assert "X" in trans_df
    assert "Y" in trans_df


def test_grouptrans():
    """Test grouping of transmissibilities"""
    eclfiles = EclFiles(DATAFILE)
    trans_df = trans.df(eclfiles, vectors="FIPNUM", group=True, coords=True)
    assert "FIPNUMPAIR" in trans_df
    assert "FIPNUM1" in trans_df
    assert "FIPNUM2" in trans_df
    assert (trans_df["FIPNUM1"] < trans_df["FIPNUM2"]).all()
    assert len(trans_df) == 7
    assert "X" in trans_df  # (average X coord for that FIPNUM interface)


def test_nx(tmpdir):
    """Test graph generation"""
    eclfiles = EclFiles(DATAFILE)
    network = trans.make_nx_graph(eclfiles, region="FIPNUM")
    assert network.number_of_nodes() == 6
    networkx.write_gexf(
        network, str(tmpdir.join("reek-fipnum-trans.gxf")), prettyprint=True
    )
    assert Path(tmpdir / "reek-fipnum-trans.gxf").is_file()


def test_main(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir / "trans.csv"
    sys.argv = ["ecl2csv", "trans", "-v", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
