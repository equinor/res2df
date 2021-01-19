import sys
import subprocess

import pytest

from .test_grid import DATAFILE


@pytest.mark.skipif(sys.version_info < (3, 7), reason="Requires Python 3.7 or higher")
@pytest.mark.parametrize("verbose", [False, True])
def test_grid_logging(tmp_path, verbose):

    commands = ["ecl2csv", "grid", DATAFILE, "--output", tmp_path / "eclgrid.csv"]
    if verbose:
        commands.append("-v")

    result = subprocess.run(commands, check=True, capture_output=True)
    output = result.stdout.decode() + result.stderr.decode()

    assert "INFO:" in output if verbose else "INFO:" not in output
