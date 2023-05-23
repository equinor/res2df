"""tests of function write_dframe_and_meta_to_file"""
import os
from pathlib import Path
from shutil import rmtree
import pandas as pd
import pyarrow.feather as pf
from fmu.config.utilities import yaml_load
import ecl2df
import pytest
import importlib
from ecl2df import bulk
from ecl2df.common import write_dframe_and_meta_to_file

TESTDIR = Path(__file__).absolute().parent
REEK_R_0 = TESTDIR / "data/reek/"
REEK_DATA_FILE = str(REEK_R_0 / "eclipse/model/2_R001_REEK-0.DATA")
CONFIG_PATH = REEK_R_0 / "fmuconfig/output/global_variables.yml"
CONFIG_PATH_W_PATH = REEK_R_0 / "fmuconfig/output/global_variables_w_eclpath.yml"
CONFIG_PATH_W_SETTINGS = (
    REEK_R_0 / "fmuconfig/output/global_variables_w_eclpath_and_extras.yml"
)


def _assert_string(string_to_assert, answer):
    """assert that string is equal to another string

    Args:
        string_to_assert (str): the string to check
        answer (str): the correct string
    """
    ass_string = f"{string_to_assert} should have been {answer}"
    assert string_to_assert == answer, ass_string


def _assert_metadata_are_produced_and_are_correct(
    tagname, correct_len=1, path=Path(".")
):
    """Assert that two files are produced, and that metadata are correct"""
    share_folder = path / "share"
    files = list(share_folder.glob("results/tables/[!.]*.*"))
    print(files)
    for file_name in files:
        print(file_name)
    nr_files = len(files)
    len_str = f"Nr of files should be {correct_len}, but is {nr_files}"
    for file_path in files:
        try:
            print(pd.read_csv(file_path).head())
        except UnicodeDecodeError:
            print(pf.read_feather(file_path).head())
        except pd.errors.EmptyDataError:
            print(f"{file_path} is empty")

        meta = yaml_load(file_path.parent / ("." + file_path.name + ".yml"))

        print(meta["data"])
        _assert_string(meta["data"]["name"], "2_R001_REEK")
        if tagname != "bulk":
            _assert_string(meta["data"]["tagname"], tagname)
        print(meta["data"]["spec"]["columns"])
        # _assert_string(meta["data"]["table_index"], ["DATE"])

    rmtree(share_folder)
    assert len(files) == correct_len, len_str


def test_write_dframe_and_meta_to_file(tmp_path):
    """Test function write_dframe_and_meta_to_file"""
    os.chdir(tmp_path)
    test = pd.DataFrame({"DATE": [1, 2, 3], "FOPT": [0, 1, 2]})
    args = {
        "DATAFILE": REEK_DATA_FILE,
        "config_path": CONFIG_PATH,
        "output": "summary.csv",
        "subcommand": "summary",
    }

    write_dframe_and_meta_to_file(test, args)
    _assert_metadata_are_produced_and_are_correct("summary", path=tmp_path)


@pytest.mark.parametrize(
    "submod_name,",
    (
        submod
        for submod in ecl2df.constants.SUBMODULES
        if submod not in ("vfp", "wellcompletiondata")
    ),
)
# vfp and wellcompletion data cannot be testing that easily
# no vfp data for Reek, no zonemap available for wellcompletion
class TestSingles:
    """Test functions for exporting one by one"""

    def test_export_w_metadata_functions(self, tmp_path, submod_name):
        """Test main entry point in each submodule

        Args:
            tmp_path (pathlib.path): temp path for tests
            submod_name (str): name of submodule
        """
        os.chdir(tmp_path)
        func = importlib.import_module("ecl2df." + submod_name).export_w_metadata
        func(REEK_DATA_FILE, CONFIG_PATH)
        _assert_metadata_are_produced_and_are_correct(submod_name)

    def test_ecl2csv_command_line_w_metadata(self, mocker, tmp_path, submod_name):
        """Test function access through ecl2csv command line tool

        Args:
            mocker (pytest.mocker): the enabler of mocking
            tmp_path (pathlib.path): temp path for tests
            submod_name (str): name of submodule
        """
        os.chdir(tmp_path)
        mocker.patch(
            "sys.argv",
            [
                "ecl2csv",
                "--config_path",
                CONFIG_PATH,
                submod_name,
                REEK_DATA_FILE,
            ],
        )
        _assert_metadata_are_produced_and_are_correct(submod_name)


def test_bulk_export(tmp_path):
    """Test bulk upload"""
    os.chdir(tmp_path)
    ecl2df.bulk.bulk_export(REEK_DATA_FILE, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("bulk", 15)


def test_limiting_bulk_export(tmp_path):
    """Test bulk upload with only one submodule"""
    os.chdir(tmp_path)
    ecl2df.bulk.bulk_export(REEK_DATA_FILE, CONFIG_PATH, ["rft"])
    _assert_metadata_are_produced_and_are_correct("rft")


def test_bulk_export_from_config(tmp_path):
    """Test bulk upload with config only"""
    os.chdir(tmp_path)
    ecl2df.bulk.bulk_export_with_configfile(CONFIG_PATH_W_PATH)
    _assert_metadata_are_produced_and_are_correct("bulk", 16, path=tmp_path)


def test_bulk_export_from_config_w_settings(tmp_path):
    """Test bulk upload with config only"""
    os.chdir(tmp_path)
    ecl2df.bulk.bulk_export_with_configfile(CONFIG_PATH_W_SETTINGS)
    # ecl2df.bulk.bulk_export_with_configfile(
    #     "/private/dbs/git/ecl2df/tests/data/reek/fmuconfig/output/global_variables_w_eclpath_and_extras.yml"
    # )
    _assert_metadata_are_produced_and_are_correct("bulk", 3, path=tmp_path)


def test_remove_numbers():
    """Test utility func"""
    string = "cadoodelo"
    test_data = string + "--1239"
    assert ecl2df.bulk.remove_numbers(test_data) == string


def test_bulk_export_from_command_line(mocker, tmp_path):
    """Test bulk upload upload option from command line

    Args:
        mocker (func): mocking function for mimicing command line
    """
    os.chdir(tmp_path)
    mocker.patch(
        "sys.argv", ["ecl2csv", "--config_path", str(CONFIG_PATH_W_PATH), "bulk"]
    )
    ecl2df.ecl2csv.main()
    _assert_metadata_are_produced_and_are_correct("bulk", 16, path=tmp_path)


if __name__ == "__main__":
    test_bulk_export_from_config_w_settings()
