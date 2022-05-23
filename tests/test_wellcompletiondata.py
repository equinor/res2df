import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ecl2df import common, wellcompletiondata
from ecl2df.eclfiles import EclFiles
from ecl2df.wellcompletiondata import _merge_compdat_and_connstatus

try:
    import opm  # noqa

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False

TESTDIR = Path(__file__).absolute().parent
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")
# EIGHTCELLS_ZONEMAP = str(TESTDIR / "data/eightcells/zones.lyr")
EIGHTCELLS_ZONEMAP = common.convert_lyrlist_to_zonemap(
    common.parse_lyrfile(str(TESTDIR / "data/eightcells/zones.lyr"))
)


def test_eightcells_with_wellconnstatus():
    """Test the Eightcells dataset with the well connection status
    option activated (connection status extracted from summary data)
    """
    eclfiles = EclFiles(EIGHTCELLS)
    expected_dframe = pd.DataFrame(
        [
            {
                "WELL": "OP1",
                "ZONE": "Upper",
                "DATE": datetime.datetime(year=2000, month=1, day=2),
                "KH": -1,
                "OP/SH": "OPEN",
            }
        ]
    )
    pd.testing.assert_frame_equal(
        wellcompletiondata.df(
            eclfiles, zonemap=EIGHTCELLS_ZONEMAP, use_wellconnstatus=True
        ),
        expected_dframe,
        check_dtype=False,
    )


def test_eightcells_without_wellconnstatus():
    """Test the Eightcells dataset with only the compdat export data (connection
    status extracted from parsing the schedule file)"""
    eclfiles = EclFiles(EIGHTCELLS)
    expected_dframe = pd.DataFrame(
        [
            {
                "WELL": "OP1",
                "ZONE": "Upper",
                "DATE": datetime.datetime(year=2000, month=1, day=1),
                "KH": -1,
                "OP/SH": "OPEN",
            }
        ]
    )
    pd.testing.assert_frame_equal(
        wellcompletiondata.df(
            eclfiles, zonemap=EIGHTCELLS_ZONEMAP, use_wellconnstatus=False
        ),
        expected_dframe,
        check_dtype=False,
    )


def test_merge_compdat_and_connstatus():
    """Tests the functionality of the merge_compdat_and_connstatus function.

    The following functionality is covered:
    * The two first rows of df_compdat is replaced with the two first from
    df_connstatus, except for the KH (which is only available in df_compdat).
    KH is taken from the first of the two compdat rows
    * The A2 well is not available in df_connstatus and will be taken as is
    from df_compdat
    * the fourth row in df_compdat (WELL: A1, REAL:1) is ignored because A1 is
    in df_connstatus, but not REAL 1. We don't mix compdat and connstatus data
    for the same well
    * The fourth row in df_compdat has KH=Nan. This will be 0 in the output
    """
    df_compdat = pd.DataFrame(
        data={
            "DATE": [
                "2021-01-01",
                "2021-05-01",
                "2021-01-01",
                "2021-01-01",
                "2022-01-01",
            ],
            "REAL": [0, 0, 0, 1, 0],
            "WELL": ["A1", "A1", "A2", "A1", "A3"],
            "I": [1, 1, 1, 1, 1],
            "J": [1, 1, 1, 1, 1],
            "K1": [1, 1, 1, 1, 1],
            "OP/SH": ["SHUT", "OPEN", "OPEN", "OPEN", "OPEN"],
            "KH": [100, 1000, 10, 100, np.nan],
            "ZONE": ["ZONE1", "ZONE1", "ZONE1", "ZONE1", "ZONE1"],
        }
    )
    df_connstatus = pd.DataFrame(
        data={
            "DATE": ["2021-03-01", "2021-08-01", "2021-01-01"],
            "REAL": [0, 0, 0],
            "WELL": ["A1", "A1", "A3"],
            "I": [1, 1, 1],
            "J": [1, 1, 1],
            "K1": [1, 1, 1],
            "OP/SH": ["OPEN", "SHUT", "OPEN"],
        }
    )
    df_output = pd.DataFrame(
        data={
            "DATE": ["2021-03-01", "2021-08-01", "2021-01-01", "2021-01-01"],
            "REAL": [0, 0, 0, 0],
            "WELL": ["A1", "A1", "A3", "A2"],
            "I": [1, 1, 1, 1],
            "J": [1, 1, 1, 1],
            "K1": [1, 1, 1, 1],
            "OP/SH": ["OPEN", "SHUT", "OPEN", "OPEN"],
            "KH": [100.0, 100.0, 0.0, 10.0],
            "ZONE": ["ZONE1", "ZONE1", "ZONE1", "ZONE1"],
        }
    )
    df_compdat["DATE"] = pd.to_datetime(df_compdat["DATE"])
    df_connstatus["DATE"] = pd.to_datetime(df_connstatus["DATE"])
    df_output["DATE"] = pd.to_datetime(df_output["DATE"])

    df_result = _merge_compdat_and_connstatus(df_compdat, df_connstatus)
    pd.testing.assert_frame_equal(df_result, df_output, check_like=True)
