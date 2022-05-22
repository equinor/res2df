import datetime
from pathlib import Path

import pandas as pd

from ecl2df import wellcompletiondata
from ecl2df.eclfiles import EclFiles

try:
    import opm  # noqa

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False

TESTDIR = Path(__file__).absolute().parent
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")
EIGHTCELLS_ZONEMAP = str(TESTDIR / "data/eightcells/zones.lyr")


def test_eightcells_dataset():
    """Test Eightcells dataset."""
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
            eclfiles, zonemap_filename=EIGHTCELLS_ZONEMAP, use_wellconnstatus=True
        ),
        expected_dframe,
        check_dtype=False,
    )

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
            eclfiles, zonemap_filename=EIGHTCELLS_ZONEMAP, use_wellconnstatus=False
        ),
        expected_dframe,
        check_dtype=False,
    )
