from pathlib import Path

import pandas as pd
import pytest

from ecl2df import wellconnstatus
from ecl2df.eclfiles import EclFiles

try:
    import opm  # noqa

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")


def test_reek_dataset():
    """Test Reek dataset. It contains no CPI data and should return
    an empty dataframe.
    """
    eclfiles = EclFiles(REEK)
    wellconnstatus_df = wellconnstatus.df(eclfiles)
    assert wellconnstatus_df.empty


def test_eightcells_dataset():
    """Test the Eightcells dataset which has CPI data"""
    eclfiles = EclFiles(EIGHTCELLS)
    wellconnstatus_df = wellconnstatus.df(eclfiles)
    expected_dframe = pd.DataFrame(
        [
            {
                "DATE": "2000-01-02",
                "WELL": "OP1",
                "I": "1",
                "J": "1",
                "K": "1",
                "OP/SH": "OPEN",
            }
        ],
    )
    expected_dframe["DATE"] = pd.to_datetime(expected_dframe["DATE"])
    pd.testing.assert_frame_equal(wellconnstatus_df, expected_dframe, check_dtype=False)


@pytest.mark.parametrize(
    "smry, expected_wellconnstatus",
    [
        # Simple Example with one well that is opened.
        # Summary vectors on wrong format is ignored
        (
            pd.DataFrame(
                [
                    ["2000-01-01", 0, 0, 0],
                    ["2000-01-02", 1.1, 1, 1000],
                ],
                columns=["DATE", "CPI:OP1:1,1,1", "CPI:OP1:123", "FOPT"],
            ),
            pd.DataFrame(
                [
                    ["2000-01-02", "OP1", "1", "1", "1", "OPEN"],
                ],
                columns=["DATE", "WELL", "I", "J", "K", "OP/SH"],
            ),
        ),
        # Two connections, and only one is never opened which gives no output
        # The other is opened from first date and then closed
        (
            pd.DataFrame(
                [
                    ["2000-01-01", 0, 1],
                    ["2000-01-02", 0, 0],
                ],
                columns=["DATE", "CPI:OP1:1,1,1", "CPI:OP1:1,1,2"],
            ),
            pd.DataFrame(
                [
                    ["2000-01-01", "OP1", "1", "1", "2", "OPEN"],
                    ["2000-01-02", "OP1", "1", "1", "2", "SHUT"],
                ],
                columns=["DATE", "WELL", "I", "J", "K", "OP/SH"],
            ),
        ),
        # Two wells. Dates containing hours
        (
            pd.DataFrame(
                [
                    ["2000-01-01", 1, 0],
                    ["2000-01-02 12:00:00", 1, 1],
                    ["2000-01-02", 0, 1],
                ],
                columns=["DATE", "CPI:OP1:1,1,1", "CPI:OP2:1,1,1"],
            ),
            pd.DataFrame(
                [
                    ["2000-01-01", "OP1", "1", "1", "1", "OPEN"],
                    ["2000-01-02", "OP1", "1", "1", "1", "SHUT"],
                    ["2000-01-02 12:00:00", "OP2", "1", "1", "1", "OPEN"],
                ],
                columns=["DATE", "WELL", "I", "J", "K", "OP/SH"],
            ),
        ),
    ],
)
def test_extract_status_changes(smry, expected_wellconnstatus):
    """Testing that the extract_status_changes function is working
    correctly with various summary input
    """
    smry["DATE"] = pd.to_datetime(smry["DATE"])
    smry.set_index("DATE", inplace=True)
    expected_wellconnstatus["DATE"] = pd.to_datetime(expected_wellconnstatus["DATE"])

    pd.testing.assert_frame_equal(
        wellconnstatus._extract_status_changes(smry),
        expected_wellconnstatus,
        check_dtype=False,
    )
