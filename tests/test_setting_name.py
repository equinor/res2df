"""Tests autosetting of file names
"""
import os
from pathlib import Path

import pytest

from ecl2df import ecl2csv
from ecl2df.common import find_name_components, make_output_name
from ecl2df.constants import SUBMODULES

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


@pytest.fixture(name="name_args", scope="session")
def _fixture_arg_names():
    """Return the name variables to test against

    Returns:
        tuple: name, submodule name, and args dict
    """
    _keep_name = "TESTING"
    _subcommand = "summary"
    _args = {
        "DATAFILE": f"{_keep_name}-123.DATA",
        "subcommand": _subcommand,
        "output": None,
    }

    return _keep_name, _subcommand, _args


def test_find_name_components(name_args):
    """Test function get_name_from_args

    Args:
        name_args (tuple): name, submodule name, and args dict
    """
    keep_name, subcommand, args = name_args
    name, tagname = find_name_components(args)
    assert name == keep_name, f"Name is {name}, but should be {keep_name}"
    assert tagname == subcommand, f"tagname is {tagname}, but should be {subcommand}"


def test_set_name_from_eclbase():
    """Test function set_name_from_args when no suffix supplied

    Args:
        name_args (tuple): name, submodule name, and args dict
    """
    args = {
        "subcommand": "mycommand",
        "DATAFILE": str(REEK),
        "output": None,
    }

    correct_name = "2_R001_REEK"
    correct_tag = "mycommand"
    name, tag = find_name_components(args)
    assert name == correct_name, f"Name is {name}, should be {correct_name}"
    assert tag == correct_tag, f"Tag is {tag}, should be {correct_tag}"


def test_set_name_from_args(name_args):
    """Test function set_name_from_args

    Args:
        name_args (tuple): name, submodule name, and args dict
    """
    keep_name, subcommand, args = name_args
    correct_name = f"{keep_name}--{subcommand}.csv"
    name = make_output_name(args)
    assert name == correct_name, f"Name is {name}, should be {correct_name}"


@pytest.mark.parametrize(
    "submod_name",
    (submod for submod in SUBMODULES if submod not in ("vfp", "wellcompletiondata")),
)
#  vfp and wellcompletion data cannot be testing that easily
# no vfp data for Reek, no zonemap available for wellcompletion
def test_command_line_name_setting(mocker, tmp_path, submod_name):
    """Test that the command line utility ecl2csv exports the right names"""
    os.chdir(tmp_path)
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            submod_name,
            REEK,
        ],
    )
    ecl2csv.main()
    outpath = tmp_path.glob("*.csv")
    file_names = list(outpath)
    assert len(file_names) == 1, "Produced more than one file"
    file_name = file_names[0]
    print(f" file name in test {file_name}")
    name, tagname = file_name.name.replace(file_name.suffix, "").split("--")
    file_name.unlink()
    print(name)
    print(tagname)
    correct_name = "2_R001_REEK"
    assert name == correct_name, f"{name} is not as planned {correct_name}"
    assert tagname == submod_name, f"tag {tagname} not as planned {submod_name}"
