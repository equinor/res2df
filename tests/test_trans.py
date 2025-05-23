"""Test module for res2df.trans"""

from pathlib import Path

import pytest

try:
    import networkx

    HAVE_NETWORKX = True
except ImportError:
    HAVE_NETWORKX = False

import pandas as pd

from res2df import res2csv, trans
from res2df.resdatafiles import ResdataFiles

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")


def test_trans():
    """Test that we can build a dataframe of transmissibilities"""
    resdatafiles = ResdataFiles(REEK)
    trans_df = trans.df(resdatafiles)
    assert "TRAN" in trans_df
    assert "DIR" in trans_df
    assert set(trans_df["DIR"].unique()) == {"I", "J", "K"}
    assert trans_df["TRAN"].sum() > 0

    trans_full_length = len(trans_df)

    # Try including some vectors:
    trans_df = trans.df(resdatafiles, vectors="FIPNUM")
    assert "FIPNUM" not in trans_df
    assert "FIPNUM1" in trans_df
    assert "EQLNUM2" not in trans_df

    trans_df = trans.df(resdatafiles, vectors=["FIPNUM", "EQLNUM"])
    assert "FIPNUM1" in trans_df
    assert "EQLNUM2" in trans_df

    trans_df = trans.df(resdatafiles, vectors="BOGUS")
    assert "BOGUS1" not in trans_df
    assert "TRAN" in trans_df  # (we should have gotten a warning only)

    assert "K" not in trans.df(resdatafiles, onlyijdir=True)["DIR"]
    assert "I" not in trans.df(resdatafiles, onlykdir=True)["DIR"]

    # A warning is logged, seems strange to filter on both, but
    # the answer (empty) makes sense given the instruction. Alternative
    # would be a ValueError.
    assert trans.df(resdatafiles, onlykdir=True, onlyijdir=True).empty

    transnnc_df = trans.df(resdatafiles, addnnc=True)
    assert len(transnnc_df) > trans_full_length

    trans_df = trans.df(resdatafiles, vectors=["FIPNUM", "EQLNUM"], boundaryfilter=True)
    assert trans_df.empty

    trans_df = trans.df(resdatafiles, vectors="FIPNUM", boundaryfilter=True)
    assert len(trans_df) < trans_full_length

    trans_df = trans.df(resdatafiles, coords=True)
    assert "X" in trans_df
    assert "Y" in trans_df


def test_grouptrans():
    """Test grouping of transmissibilities"""
    resdatafiles = ResdataFiles(REEK)
    trans_df = trans.df(resdatafiles, vectors="FIPNUM", group=True, coords=True)
    assert "FIPNUMPAIR" in trans_df
    assert "FIPNUM1" in trans_df
    assert "FIPNUM2" in trans_df
    assert (trans_df["FIPNUM1"] < trans_df["FIPNUM2"]).all()
    assert len(trans_df) == 7
    assert "X" in trans_df  # (average X coord for that FIPNUM interface)

    # This gives a logged error:
    assert trans.df(resdatafiles, vectors=["FIPNUM", "EQLNUM"], group=True).empty


@pytest.mark.skipif(not HAVE_NETWORKX, reason="Requires networkx being installed")
def test_nx(tmp_path):
    """Test graph generation"""
    resdatafiles = ResdataFiles(REEK)
    network = trans.make_nx_graph(resdatafiles, region="FIPNUM")
    assert network.number_of_nodes() == 6
    networkx.write_gexf(network, tmp_path / "reek-fipnum-trans.gxf", prettyprint=True)
    assert (tmp_path / "reek-fipnum-trans.gxf").is_file()


def test_main(tmp_path, mocker):
    """Test command line interface"""
    tmpcsvfile = tmp_path / "trans.csv"
    mocker.patch(
        "sys.argv", ["res2csv", "trans", "-v", EIGHTCELLS, "-o", str(tmpcsvfile)]
    )
    res2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
