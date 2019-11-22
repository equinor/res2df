# -*- coding: utf-8 -*-
"""Test module for ecl2df.trans"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import datetime
import pandas as pd

import pytest

from ecl2df import trans
from ecl2df import ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_trans():
    """Test that we can build a dataframe of transmissibilities"""
    eclfiles = EclFiles(DATAFILE)
    trans_df = trans.df(eclfiles)
    assert "TRAN" in trans_df
    assert "DIR" in trans_df
    assert set(trans_df["DIR"].unique()) == set(["I", "J", "K"])
    assert trans_df["TRAN"].sum() > 0

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

    # Example creating a column with the FIPNUM pair as a string
    # (lowest fipnum value first)
    trans_df = trans.df(eclfiles, vectors=["X", "Y", "Z", "FIPNUM"])
    trans_df["FIPNUMPAIR"] = [
        str(int(min((x[1:3])))) + "-" + str(int(max(x[1:3])))
        for x in trans_df[["FIPNUM1", "FIPNUM2"]].itertuples()
    ]
    # Filter to different FIPNUMS (that means FIPNUM boundaries)
    # and horizontal connetions:
    filt_trans_df = trans_df[
        (trans_df["FIPNUM1"] != trans_df["FIPNUM2"]) & (trans_df["DIR"] != "K")
    ]
    unique_pairs = filt_trans_df["FIPNUMPAIR"].unique()
    assert len(unique_pairs) == 3
    assert "5-6" in unique_pairs
    assert "6-5" not in unique_pairs  # because we have sorted them

    assert len(filt_trans_df) < len(trans_df)
    assert set(filt_trans_df["DIR"].unique()) == set(["I", "J"])
    # filt_trans_df.to_csv("fipnumtrans.csv", index=False)


def test_main(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-trans.csv")
    sys.argv = ["ecl2csv", "trans", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()
    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
