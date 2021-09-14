"""Test installation"""

import subprocess

import pytest

import ecl2df

try:
    import opm  # noqa
except ImportError:
    pytest.skip(
        "OPM is not installed, command line client does not work without it.",
        allow_module_level=True,
    )


@pytest.mark.integration
def test_integration():
    """Test that all endpoints that are to be installed are installed"""
    assert subprocess.check_output(["ecl2csv", "-h"])  # nosec
    assert subprocess.check_output(["csv2ecl", "-h"])  # nosec

    # The subparsers should exit "cleanly" with exit code 2 ("Incorrect usage")
    # when no more options are provided on the command line
    with pytest.raises(subprocess.CalledProcessError) as exception:
        subprocess.check_output(["ecl2csv"])  # nosec
        assert exception.value.returncode == 2
    with pytest.raises(subprocess.CalledProcessError) as exception:
        subprocess.check_output(["csv2ecl"])  # nosec
        assert exception.value.returncode == 2
    # ref: https://stackoverflow.com/questions/23714542/  \
    #              why-does-pythons-argparse-use-an-error-code-of-2-for-systemexit

    for submodule in ecl2df.SUBMODULES:
        helptext = subprocess.check_output(["ecl2csv", submodule, "-h"])
        # Test that this option is hidden, the argument is only there
        # to support optional number of arguments in ERT forward models.
        assert "hiddenemptyplaceholders" not in str(helptext)
