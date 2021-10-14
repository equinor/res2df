from pathlib import Path

import pandas as pd

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


def test_eightcells_dataset():
    """Test Eightcells dataset"""
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