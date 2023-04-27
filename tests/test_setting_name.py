"""Tests autosetting of file names
"""
import os
from pathlib import Path
import pytest
from ecl2df.common import get_names_from_args, set_name_from_args
from ecl2df import ecl2csv

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


@pytest.fixture(name="name_args", scope="session")
def _fixture_arg_names():
    _keep_name = "TESTING"
    _subcommand = "summary"
    _args = {"DATAFILE": f"{_keep_name}-123.DATA", "subcommand": _subcommand}

    return _keep_name, _subcommand, _args


def test_get_name_from_args(name_args):
    """Test function get_name_from_args"""
    keep_name, subcommand, args = name_args
    name, tagname, content = get_names_from_args(args)
    assert name == keep_name, f"Name is {name}, but should be {keep_name}"
    assert tagname == subcommand, f"tagname is {tagname}, but should be {subcommand}"
    assert content == "timeseries", f"Content is {content}, but should be timeseries"


def test_set_name_from_args(name_args):
    keep_name, subcommand, args = name_args
    correct_name = f"{keep_name}--{subcommand}.csv"
    name = set_name_from_args(args)
    assert name == correct_name, f"Name is {name}, should be {correct_name}"


@pytest.mark.integration
def test_summmary_name(mocker, tmp_path):
    """Test that the command line utility ecl2csv exports the right names"""
    os.chdir(tmp_path)
    print(tmp_path)
    module_names = [
        "compdat",
        "equil",
        "faults",
        "fipreports",
        "grid",
        # "grouptree",
        "nnc",
        "pillars",
        "pvt",
        "rft",
        "summary",
        "satfunc",
        "trans",
        "wcon",
        "wellcompletiondata",
        "wellconnstatus",
    ]
    for module_name in module_names:
        print(module_name)
        mocker.patch(
            "sys.argv",
            [
                "ecl2csv",
                module_name,
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
        assert tagname == module_name, f"tag {tagname} not as planned {module_name}"
