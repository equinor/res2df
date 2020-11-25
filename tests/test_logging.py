import argparse

import pytest

from ecl2df.grid import grid_main
from test_grid import DATAFILE


@pytest.mark.parametrize("verbose", [False, True])
def test_grid_logging(caplog, tmp_path, verbose):

    args = argparse.Namespace(
        verbose=verbose,
        DATAFILE=DATAFILE,
        vectors="*",
        rstdates="",
        dropconstants=False,
        stackdates=False,
        output=tmp_path / "eclgrid.csv",
    )

    grid_main(args)

    if verbose:
        assert caplog.records
    else:
        assert caplog.records == []
