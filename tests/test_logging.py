import subprocess
import sys

import pytest

from .test_grid import EIGHTCELLS

try:
    import opm  # noqa

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False


@pytest.mark.skipif(not HAVE_OPM, reason="Command line client requires OPM")
@pytest.mark.skipif(sys.version_info < (3, 7), reason="Requires Python 3.7 or higher")
@pytest.mark.parametrize("verbose", [False, True])
def test_grid_logging(tmp_path, verbose):

    commands = ["ecl2csv", "grid", EIGHTCELLS, "--output", tmp_path / "eclgrid.csv"]
    if verbose:
        commands.append("-v")

    result = subprocess.run(commands, check=True, capture_output=True)
    output = result.stdout.decode() + result.stderr.decode()

    assert "INFO:" in output if verbose else "INFO:" not in output
