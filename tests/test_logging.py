import subprocess

import pytest

from ecl2df.grid import grid_main
from test_grid import DATAFILE


@pytest.mark.parametrize("verbose", [False, True])
def test_grid_logging(tmp_path, verbose):

    commands = ["ecl2csv", "grid", DATAFILE, "--output", tmp_path / "eclgrid.csv"]
    if verbose:
        commands.append("-v")

    result = subprocess.run(commands, check=True, capture_output=True)

    if verbose:
        assert "INFO:" in result.stderr.decode()
    else:
        assert "INFO:" not in result.stderr.decode()
