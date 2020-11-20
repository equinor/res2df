"""Test module for ecl2df.common"""

import pandas as pd

from ecl2df import common


def test_opmkeywords():
    """Test that we have loaded some keyword metadata from json files on disk"""
    assert "WCONPROD" in common.OPMKEYWORDS
    assert common.OPMKEYWORDS["WCONPROD"]
    assert "name" in common.OPMKEYWORDS["WCONPROD"]
    assert "BHP" in [x["name"] for x in common.OPMKEYWORDS["WCONPROD"]["items"]]

    # This file should not be parsed..
    assert "README" not in common.OPMKEYWORDS


def test_stack_on_colname():
    """Test that we can stack column with an implicit double level
    in the column names indicated by a separator string"""

    dframe = pd.DataFrame(
        columns=["EQLNUM", "STATIC", "OWC@2000-01-01", "OWC@2020-01-01"],
        data=[[1, 1.2, 2000, 1900], [2, 1.3, 2100, 2050]],
    )
    stacked = common.stack_on_colnames(dframe)
    assert "DATE" in stacked
    assert "OWC" in stacked
    assert len(stacked.columns) == 4
    assert len(stacked["DATE"].unique()) == 2
    assert len(stacked) == 4
    assert not stacked.isnull().sum().sum()

    dframe = pd.DataFrame(
        columns=[
            "EQLNUM",
            "STATIC",
            "OWC@2000-01-01",
            "OWC@2020-01-01",
            "GOC@2000-01-01",
            "GOC@2020-01-01",
        ],
        data=[[1, 1.2, 2000, 1900, 1800, 1700], [2, 1.3, 2100, 2050, 2000, 1950]],
    )
    stacked = common.stack_on_colnames(dframe)
    assert "DATE" in stacked
    assert "OWC" in stacked
    assert "GOC" in stacked
    assert len(stacked.columns) == 5
    assert len(stacked["DATE"].unique()) == 2
    assert len(stacked) == 4
    assert not stacked.isnull().sum().sum()

    dframe = pd.DataFrame(
        columns=["OWC@2000-01-01", "OWC@2020-01-01"], data=[[2000, 1900], [2100, 2050]]
    )
    stacked = common.stack_on_colnames(dframe)
    assert "DATE" in stacked
    assert "OWC" in stacked
    assert len(stacked.columns) == 2
    assert len(stacked["DATE"].unique()) == 2
    assert len(stacked) == 4
    assert not stacked.isnull().sum().sum()

    dframe = pd.DataFrame(columns=["EQLNUM", "STATIC"], data=[[1, 1.2], [2, 1.3]])
    stacked = common.stack_on_colnames(dframe)
    assert "DATE" not in stacked
    assert "OWC" not in stacked
    assert "EQLNUM" in stacked
    assert "STATIC" in stacked
    assert len(stacked.columns) == 2
    assert len(stacked) == 2
    assert not stacked.isnull().sum().sum()


def test_eclcompress():
    """Test that we can compress string using Eclipse style
    run-length encoding"""
    assert common.runlength_eclcompress("") == ""
    assert common.runlength_eclcompress(" ") == ""
    assert common.runlength_eclcompress("1 2") == "1  2"
    assert common.runlength_eclcompress("1 2", sep=" ") == "1 2"
    assert common.runlength_eclcompress("1 2", sep="   ") == "1   2"
    assert common.runlength_eclcompress("1") == "1"
    assert common.runlength_eclcompress("1 1") == "2*1"
    assert common.runlength_eclcompress("1 1 1") == "3*1"
    assert common.runlength_eclcompress("1     1 1") == "3*1"
    assert common.runlength_eclcompress("1  \n  1 1 2") == "3*1  2"
