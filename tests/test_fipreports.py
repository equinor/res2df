"""Test module for fipreports"""

import sys
from pathlib import Path
import datetime

import pandas as pd
import numpy as np

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


def test_prtstring(tmpdir):
    """Test a PRT from string, verifying every detail of the dataframe"""
    prtstring = """
  REPORT   0     1 JAN 2000
                                                =================================
                                                : FIPNUM  REPORT REGION    2    :
                                                :     PAV =        139.76  BARSA:
                                                :     PORV=     27777509.   RM3 :
                           :--------------- OIL    SM3  ---------------:-- WAT    SM3  -:--------------- GAS    SM3  ---------------:
                           :     LIQUID         VAPOUR         TOTAL   :       TOTAL    :       FREE      DISSOLVED         TOTAL   :
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :CURRENTLY IN PLACE       :     21091398.                    21091398.:       4590182. :           -0.    483594842.     483594842.:
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :OUTFLOW TO OTHER REGIONS :        76266.                       76266.:         75906. :            0.      1818879.       1818879.:
 :OUTFLOW THROUGH WELLS    :                                         0.:             0. :                                         0.:
 :MATERIAL BALANCE ERROR.  :                                         0.:             0. :                                         0.:
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :ORIGINALLY IN PLACE      :     21136892.                    21136892.:       4641214. :            0.    484657561.     484657561.:
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :OUTFLOW TO REGION   1    :       143128.                      143128.:       -161400. :            0.      3017075.       3017075.:
 :OUTFLOW TO REGION   3    :       -66862.                      -66862.:        198900. :           -0.     -1198195.      -1198195.:
 :OUTFLOW TO REGION   8    :            0.                           0.:         38405. :            0.            0.             0.:
 ====================================================================================================================================
"""  # noqa
    tmpdir.chdir()
    Path("FOO.PRT").write_text(prtstring)
    dframe = fipreports.df("FOO.PRT")
    expected_dframe = pd.DataFrame(
        [
            {
                "DATE": datetime.date(2000, 1, 1),
                "FIPNAME": "FIPNUM",
                "REGION": 2,
                "DATATYPE": "CURRENTLY IN PLACE",
                "TO_REGION": np.nan,
                "STOIIP_OIL": 21091398.0,
                "ASSOCIATEDOIL_GAS": None,
                "STOIIP_TOTAL": 21091398.0,
                "WIIP_TOTAL": 4590182.0,
                "GIIP_GAS": -0.0,
                "ASSOCIATEDGAS_OIL": 483594842.0,
                "GIIP_TOTAL": 483594842.0,
            },
            {
                "DATE": datetime.date(2000, 1, 1),
                "FIPNAME": "FIPNUM",
                "REGION": 2,
                "DATATYPE": "OUTFLOW TO OTHER REGIONS",
                "TO_REGION": np.nan,
                "STOIIP_OIL": 76266.0,
                "ASSOCIATEDOIL_GAS": None,
                "STOIIP_TOTAL": 76266.0,
                "WIIP_TOTAL": 75906.0,
                "GIIP_GAS": 0.0,
                "ASSOCIATEDGAS_OIL": 1818879.0,
                "GIIP_TOTAL": 1818879.0,
            },
            {
                "DATE": datetime.date(2000, 1, 1),
                "FIPNAME": "FIPNUM",
                "REGION": 2,
                "DATATYPE": "OUTFLOW THROUGH WELLS",
                "TO_REGION": np.nan,
                "STOIIP_OIL": np.nan,
                "ASSOCIATEDOIL_GAS": None,
                "STOIIP_TOTAL": 0.0,
                "WIIP_TOTAL": 0.0,
                "GIIP_GAS": np.nan,
                "ASSOCIATEDGAS_OIL": np.nan,
                "GIIP_TOTAL": 0.0,
            },
            {
                "DATE": datetime.date(2000, 1, 1),
                "FIPNAME": "FIPNUM",
                "REGION": 2,
                "DATATYPE": "MATERIAL BALANCE ERROR.",
                "TO_REGION": np.nan,
                "STOIIP_OIL": np.nan,
                "ASSOCIATEDOIL_GAS": None,
                "STOIIP_TOTAL": 0.0,
                "WIIP_TOTAL": 0.0,
                "GIIP_GAS": np.nan,
                "ASSOCIATEDGAS_OIL": np.nan,
                "GIIP_TOTAL": 0.0,
            },
            {
                "DATE": datetime.date(2000, 1, 1),
                "FIPNAME": "FIPNUM",
                "REGION": 2,
                "DATATYPE": "ORIGINALLY IN PLACE",
                "TO_REGION": np.nan,
                "STOIIP_OIL": 21136892.0,
                "ASSOCIATEDOIL_GAS": None,
                "STOIIP_TOTAL": 21136892.0,
                "WIIP_TOTAL": 4641214.0,
                "GIIP_GAS": 0.0,
                "ASSOCIATEDGAS_OIL": 484657561.0,
                "GIIP_TOTAL": 484657561.0,
            },
            {
                "DATE": datetime.date(2000, 1, 1),
                "FIPNAME": "FIPNUM",
                "REGION": 2,
                "DATATYPE": "OUTFLOW TO REGION",
                "TO_REGION": 1.0,
                "STOIIP_OIL": 143128.0,
                "ASSOCIATEDOIL_GAS": None,
                "STOIIP_TOTAL": 143128.0,
                "WIIP_TOTAL": -161400.0,
                "GIIP_GAS": 0.0,
                "ASSOCIATEDGAS_OIL": 3017075.0,
                "GIIP_TOTAL": 3017075.0,
            },
            {
                "DATE": datetime.date(2000, 1, 1),
                "FIPNAME": "FIPNUM",
                "REGION": 2,
                "DATATYPE": "OUTFLOW TO REGION",
                "TO_REGION": 3.0,
                "STOIIP_OIL": -66862.0,
                "ASSOCIATEDOIL_GAS": None,
                "STOIIP_TOTAL": -66862.0,
                "WIIP_TOTAL": 198900.0,
                "GIIP_GAS": -0.0,
                "ASSOCIATEDGAS_OIL": -1198195.0,
                "GIIP_TOTAL": -1198195.0,
            },
            {
                "DATE": datetime.date(2000, 1, 1),
                "FIPNAME": "FIPNUM",
                "REGION": 2,
                "DATATYPE": "OUTFLOW TO REGION",
                "TO_REGION": 8.0,
                "STOIIP_OIL": 0.0,
                "ASSOCIATEDOIL_GAS": None,
                "STOIIP_TOTAL": 0.0,
                "WIIP_TOTAL": 38405.0,
                "GIIP_GAS": 0.0,
                "ASSOCIATEDGAS_OIL": 0.0,
                "GIIP_TOTAL": 0.0,
            },
        ]
    )

    pd.testing.assert_frame_equal(dframe, expected_dframe)


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
