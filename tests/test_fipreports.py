"""Test module for fipreports"""

import datetime
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ecl2df import ecl2csv, fipreports
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


def test_opm_prt_file():
    """Test parsing a PRT file from OPM"""
    fipreport_df = fipreports.df(
        TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0-OPMFLOW.PRT"
    )
    assert len(fipreport_df) == 530
    assert len(fipreport_df["DATE"].unique()) == 38
    assert set(fipreport_df["REGION"]) == {1, 2, 3, 4, 5, 6}
    assert set(
        [
            "DATE",
            "FIPNAME",
            "REGION",
            "DATATYPE",
            "STOIIP_OIL",
            "ASSOCIATEDOIL_GAS",
            "STOIIP_TOTAL",
            "WIIP_TOTAL",
            "GIIP_GAS",
            "ASSOCIATEDGAS_OIL",
            "GIIP_TOTAL",
        ]
    ).issubset(set(fipreport_df.columns))


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

    with pytest.raises(ValueError):
        fipreports.df(MOCKPRTFILE, fipname="WIPNUM")

    # fipname at most 8 characters:
    assert fipreports.df(MOCKPRTFILE, fipname="FIP45678").empty

    with pytest.raises(ValueError):
        fipreports.df(MOCKPRTFILE, fipname="FIP456789")


def test_prtstring(tmp_path):
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
    os.chdir(tmp_path)
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


def test_drygas_report(tmp_path):
    """Excerpt from a two-phase gas water run"""
    prtstring = """
                                                =================================
                                                : FIPNUM  REPORT REGION    2    :
                                                :     PAV =        909.34  BARSA:
                                                :     PORV=    150001895.   RM3 :
                           :--------------- OIL    SM3  ---------------:-- WAT    SM3  -:--------------- GAS    SM3  ---------------:
                           :     LIQUID         VAPOUR         TOTAL   :       TOTAL    :       FREE      DISSOLVED         TOTAL   :
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :CURRENTLY IN PLACE       :            0.                           0.:      10476036. :   1815774165.                  1815774165.:
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :OUTFLOW TO OTHER REGIONS :            0.                           0.:             0. :            0.                           0.:
 :OUTFLOW THROUGH WELLS    :                                         0.:             0. :                                         0.:
 :MATERIAL BALANCE ERROR.  :                                        -0.:             0. :                                         0.:
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :ORIGINALLY IN PLACE      :            0.                           0.:      10476036. :   1815774165.                  1815774165.:
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 ====================================================================================================================================
"""  # noqa
    os.chdir(tmp_path)
    Path("FOO.PRT").write_text(prtstring)
    dframe = fipreports.df("FOO.PRT").set_index("DATATYPE")
    assert dframe["REGION"].unique() == [2]
    pd.testing.assert_frame_equal(
        dframe.reset_index().drop(["DATE", "REGION"], axis="columns"),
        pd.DataFrame(
            [
                {
                    "DATATYPE": "CURRENTLY IN PLACE",
                    "FIPNAME": "FIPNUM",
                    "TO_REGION": None,
                    "STOIIP_OIL": 0.0,
                    "ASSOCIATEDOIL_GAS": None,
                    "STOIIP_TOTAL": 0.0,
                    "WIIP_TOTAL": 10476036.0,
                    "GIIP_GAS": 1815774165.0,
                    "ASSOCIATEDGAS_OIL": None,
                    "GIIP_TOTAL": 1815774165.0,
                },
                {
                    "DATATYPE": "OUTFLOW TO OTHER REGIONS",
                    "FIPNAME": "FIPNUM",
                    "TO_REGION": None,
                    "STOIIP_OIL": 0.0,
                    "ASSOCIATEDOIL_GAS": None,
                    "STOIIP_TOTAL": 0.0,
                    "WIIP_TOTAL": 0.0,
                    "GIIP_GAS": 0.0,
                    "ASSOCIATEDGAS_OIL": None,
                    "GIIP_TOTAL": 0.0,
                },
                {
                    "DATATYPE": "OUTFLOW THROUGH WELLS",
                    "FIPNAME": "FIPNUM",
                    "TO_REGION": None,
                    "STOIIP_OIL": np.nan,
                    "ASSOCIATEDOIL_GAS": None,
                    "STOIIP_TOTAL": 0.0,
                    "WIIP_TOTAL": 0.0,
                    "GIIP_GAS": np.nan,
                    "ASSOCIATEDGAS_OIL": None,
                    "GIIP_TOTAL": 0.0,
                },
                {
                    "DATATYPE": "MATERIAL BALANCE ERROR.",
                    "FIPNAME": "FIPNUM",
                    "TO_REGION": None,
                    "STOIIP_OIL": np.nan,
                    "ASSOCIATEDOIL_GAS": None,
                    "STOIIP_TOTAL": -0.0,
                    "WIIP_TOTAL": 0.0,
                    "GIIP_GAS": np.nan,
                    "ASSOCIATEDGAS_OIL": None,
                    "GIIP_TOTAL": 0.0,
                },
                {
                    "DATATYPE": "ORIGINALLY IN PLACE",
                    "FIPNAME": "FIPNUM",
                    "TO_REGION": None,
                    "STOIIP_OIL": 0.0,
                    "ASSOCIATEDOIL_GAS": None,
                    "STOIIP_TOTAL": 0.0,
                    "WIIP_TOTAL": 10476036.0,
                    "GIIP_GAS": 1815774165.0,
                    "ASSOCIATEDGAS_OIL": None,
                    "GIIP_TOTAL": 1815774165.0,
                },
            ]
        ),
    )


def test_rogue_eclipse_output(tmp_path):
    """The stars in the material balance error line has been observed in reality."""
    prtstring = """
                                                =================================
                                                : FIPNUM  REPORT REGION  120    :
                                                :     PAV =        298.89  BARSA:
                                                :     PORV=      4502843.   RM3 :
                           :--------------- OIL    SM3  ---------------:-- WAT    SM3  -:--------------- GAS    SM3  ---------------:
                           :     LIQUID         VAPOUR         TOTAL   :       TOTAL    :       FREE      DISSOLVED         TOTAL   :
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :CURRENTLY IN PLACE       :     -2703242.        10451.      -2692791.:       2568336. :     59233087. 190842667352.  190901900439.:
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :OUTFLOW TO OTHER REGIONS :       294586.         6362.        300947.:       1235671. :     39452538.     51855907.      91308445.:
 :OUTFLOW THROUGH WELLS    :                                     65430.:      -1818966. :                                 -85526625.:
 :MATERIAL BALANCE ERROR.  :                                   3419391.:        671761. :                              *************:
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
"""  # noqa
    os.chdir(tmp_path)
    Path("FOO.PRT").write_text(prtstring)
    dframe = fipreports.df("FOO.PRT").set_index("DATATYPE")
    assert np.isnan(dframe.loc["MATERIAL BALANCE ERROR.", "GIIP_TOTAL"])


def test_prtstring_opmflow(tmp_path):
    """Test parsing the PRT output from OPM flow."""
    prtstring = """
Starting time step 3, stepsize 19.6 days, at day 11.4/31, date = 12-Jan-2000

                                                  ===================================================
                                                  :        FIPNUM report region   1                 :
                                                  :      PAV  =       306.192 BARSA                 :
                                                  :      PORV =      78804306   RM3                 :
                         :--------------- Oil    SM3 ---------------:-- Wat    SM3 --:--------------- Gas    SM3 ---------------:
                         :      Liquid        Vapour        Total   :      Total     :      Free        Dissolved       Total   :
:------------------------:------------------------------------------:----------------:------------------------------------------:
:Currently   in place    :      16528782             0      16528782:     60416351   :             0             0             0:
:------------------------:------------------------------------------:----------------:------------------------------------------:
:Originally  in place    :      16530271             0      16530271:     60415965   :             0             0             0:
:========================:==========================================:================:==========================================:
"""  # noqa
    os.chdir(tmp_path)
    Path("FOO.PRT").write_text(prtstring)
    dframe = fipreports.df("FOO.PRT")
    print(dframe.to_dict(orient="records"))
    expected_dframe = pd.DataFrame(
        [
            {
                "DATE": datetime.date(2000, 1, 12),
                "FIPNAME": "FIPNUM",
                "REGION": 1,
                "DATATYPE": "CURRENTLY IN PLACE",
                "TO_REGION": None,
                "STOIIP_OIL": 16528782.0,
                "ASSOCIATEDOIL_GAS": 0.0,
                "STOIIP_TOTAL": 16528782.0,
                "WIIP_TOTAL": 60416351.0,
                "GIIP_GAS": 0.0,
                "ASSOCIATEDGAS_OIL": 0.0,
                "GIIP_TOTAL": 0.0,
            },
            {
                "DATE": datetime.date(2000, 1, 12),
                "FIPNAME": "FIPNUM",
                "REGION": 1,
                "DATATYPE": "ORIGINALLY IN PLACE",
                "TO_REGION": None,
                "STOIIP_OIL": 16530271.0,
                "ASSOCIATEDOIL_GAS": 0.0,
                "STOIIP_TOTAL": 16530271.0,
                "WIIP_TOTAL": 60415965.0,
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


def test_cmdline(tmp_path, mocker):
    """Test command line interface"""
    tmpcsvfile = tmp_path / "TMP-fipreports.csv"
    mocker.patch(
        "sys.argv",
        ["ecl2csv", "fipreports", "-v", DATAFILE, "--output", str(tmpcsvfile)],
    )
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(tmpcsvfile)
    assert "FIPNAME" in disk_df
    assert "STOIIP_OIL" in disk_df
    assert not disk_df.empty

    # Debug mode:
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "fipreports",
            "--debug",
            DATAFILE,
            "--output",
            "debugmode.csv",
        ],
    )
    ecl2csv.main()
    pd.testing.assert_frame_equal(pd.read_csv("debugmode.csv"), disk_df)

    # Directly on PRT file:
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "fipreports",
            DATAFILE.replace("DATA", "PRT"),
            "--output",
            "fromprtfile.csv",
        ],
    )
    ecl2csv.main()
    pd.testing.assert_frame_equal(pd.read_csv("fromprtfile.csv"), disk_df)
