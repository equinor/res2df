from pathlib import Path

from ecl2df import wellconnstatus

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
    wellconnstatus_df = wellconnstatus.df(EIGHTCELLS)
    print(wellconnstatus_df)
    assert wellconnstatus_df.empty
