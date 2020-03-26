"""Test installation"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import ecl2df

import pytest
import subprocess


@pytest.mark.integration
def test_integration():
    """Test that all endpoints that are to be installed are installed"""
    assert subprocess.check_output(["ecl2csv", "-h"])

    # Also test the deprecated modules, remove later:
    assert subprocess.check_output(["nnc2csv", "-h"])
    assert subprocess.check_output(["eclgrid2csv", "-h"])
    assert subprocess.check_output(["grid2csv", "-h"])
    assert subprocess.check_output(["summary2csv", "-h"])
    assert subprocess.check_output(["rft2csv", "-h"])
    assert subprocess.check_output(["compdat2csv", "-h"])
    assert subprocess.check_output(["equil2csv", "-h"])
    assert subprocess.check_output(["gruptree2csv", "-h"])
    assert subprocess.check_output(["satfunc2csv", "-h"])
    assert subprocess.check_output(["faults2csv", "-h"])
    assert subprocess.check_output(["wcon2csv", "-h"])
