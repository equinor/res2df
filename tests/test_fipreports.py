"""Test module for fipreports"""

import sys
from pathlib import Path

import pandas as pd

from ecl2df import fipreports, ecl2csv
from ecl2df.eclfiles import EclFiles
from ecl2df.fipreports import report_block_lineparser as parser

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
MOCKPRTFILE = str(TESTDIR / "data/fipreports/TEST1.PRT")


def test_fipreports2df():
    """Test parsing of Reek dataset"""
    prtfile = EclFiles(DATAFILE).get_prtfilename()
    fipreport_df = fipreports.df(prtfile)
    assert len(fipreport_df["REGION"].unique()) == 6
    assert len(fipreport_df["DATE"].unique()) == 1
    assert fipreport_df["FIPNAME"].unique()[0] == "FIPNUM"
    assert len(fipreport_df["DATATYPE"].unique()) == 5


def test_mockprtfile():
    """
    Test (a) mocked PRT file(s)
    """
    dframe = fipreports.df(MOCKPRTFILE)
    assert dframe["FIPNAME"].unique() == "FIPNUM"
    assert len(dframe["DATE"].unique()) == 1
    assert int(dframe.loc[0, "GIIP_GAS"]) == 20

    dframe = fipreports.df(MOCKPRTFILE, fipname="FIPZON")
    assert dframe["FIPNAME"].unique() == "FIPZON"
    assert len(dframe["REGION"].unique()) == 2
    assert len(dframe["TO_REGION"].dropna().unique()) == 4
    assert len(dframe["DATE"].unique()) == 3
    assert len(dframe["DATATYPE"].unique()) == 6

    dframe = fipreports.df(MOCKPRTFILE, fipname="FIPOWG")
    assert dframe["FIPNAME"].unique() == "FIPOWG"
    assert len(dframe["DATE"].unique()) == 1


def test_report_block_lineparser():
    """
    Test the line-parser, which has to infer partly which phases are present.
    """

    tup = parser(
        " :OUTFLOW THROUGH WELLS    :                                         0.:"
        "             0. :                                         0.:"
    )
    assert tup[0] == "OUTFLOW THROUGH WELLS"
    assert not tup[1]  # to_region is N/A
    assert not tup[2]
    assert not tup[3]
    assert tup[4] == 0.0
    assert tup[5] == 0.0
    assert not tup[6]
    assert not tup[7]
    assert tup[8] == 0.0

    assert not parser("")
    assert not parser("foobarcom")

    tup = parser(
        " :CURRENTLY IN PLACE       :    610520867.                   610520867.:"
        "    5096189976. :            0.  22298026321.   22298026321.:"
    )
    assert tup[0] == "CURRENTLY IN PLACE"
    assert not tup[1]  # to_region is N/A
    assert int(tup[2]) == 610520867
    assert not tup[3]
    assert int(tup[6]) == 0
    assert int(tup[7]) == 22298026321


def test_cmdline(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir / "TMP-fipreports.csv"
    sys.argv = ["ecl2csv", "fipreports", "-v", DATAFILE, "--output", str(tmpcsvfile)]
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(tmpcsvfile)
    assert "FIPNAME" in disk_df
    assert "STOIIP_OIL" in disk_df
    assert not disk_df.empty
