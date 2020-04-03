"""Test installation"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import subprocess

import pytest


@pytest.mark.integration
def test_integration():
    """Test that all endpoints that are to be installed are installed"""
    assert subprocess.check_output(["ecl2csv", "-h"])  # nosec
    assert subprocess.check_output(["csv2ecl", "-h"])  # nosec

    # The subparsers is tricky between py2, py36 and py37
    # and should exit cleanly with exit code 2 ("Incorrect usage")
    # when no more options are provided on the command line
    with pytest.raises(subprocess.CalledProcessError) as exception:
        subprocess.check_output(["ecl2csv"])  # nosec
        assert exception.value.returncode == 2
    with pytest.raises(subprocess.CalledProcessError) as exception:
        subprocess.check_output(["csv2ecl"])  # nosec
        assert exception.value.returncode == 2
    # ref: https://stackoverflow.com/questions/23714542/why-does-pythons-argparse-use-an-error-code-of-2-for-systemexit

    # Also test the deprecated modules, remove later:
    assert subprocess.check_output(["compdat2csv", "-h"])  # nosec
    assert subprocess.check_output(["eclgrid2csv", "-h"])  # nosec
    assert subprocess.check_output(["equil2csv", "-h"])  # nosec
    assert subprocess.check_output(["faults2csv", "-h"])  # nosec
    assert subprocess.check_output(["grid2csv", "-h"])  # nosec
    assert subprocess.check_output(["gruptree2csv", "-h"])  # nosec
    assert subprocess.check_output(["nnc2csv", "-h"])  # nosec
    assert subprocess.check_output(["rft2csv", "-h"])  # nosec
    assert subprocess.check_output(["satfunc2csv", "-h"])  # nosec
    assert subprocess.check_output(["summary2csv", "-h"])  # nosec
    assert subprocess.check_output(["wcon2csv", "-h"])  # nosec
