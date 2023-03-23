"""tests of function write_dframe_and_meta_to_file"""
from argparse import Namespace
from pathlib import Path
from shutil import rmtree
import pandas as pd
from fmu.config.utilities import yaml_load
import ecl2df
from ecl2df.common import write_dframe_and_meta_to_file

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
META_PATH = TESTDIR / "data/reek/fmuconfig/output/global_variables.yml"


def _assert_string(string_to_assert, answer):
    """assert that string is equal to another string

    Args:
        string_to_assert (str): the string to check
        answer (str): the correct string
    """
    ass_string = f"{string_to_assert} should have been {answer}"
    assert string_to_assert == answer, ass_string


def _assert_metadata_are_produced_and_are_correct():
    """Assert that two files are produced, and that metadata are correct"""
    share_folder = Path("share/")
    files = list(share_folder.glob("results/tables/*.*"))
    print(files)
    assert len(files) == 2, "produced different to two files"
    for file_path in files:
        if file_path.name.startswith("."):
            meta = yaml_load(file_path)
            print(meta["data"])
            _assert_string(meta["data"]["name"], "2_R001_REEK")
            _assert_string(meta["data"]["tagname"], "summary")
            _assert_string(meta["data"]["table_index"], ["DATE"])
        else:
            print(pd.read_csv(file_path).head())

    rmtree(share_folder)


def test_write_dframe_and_meta_to_file():
    """Test function write_dframe_and_meta_to_file"""
    test = pd.DataFrame({"DATE": [1, 2, 3], "FOPT": [0, 1, 2]})
    args = Namespace(
        DATAFILE=REEK, metadata=META_PATH, output="summary.csv", subcommand="summary"
    )

    write_dframe_and_meta_to_file(test, args)
    _assert_metadata_are_produced_and_are_correct()


def test_write_through_summary_main():
    """Test summary main entry point"""

    ecl2df.summary.export_w_metadata(REEK, META_PATH)
    _assert_metadata_are_produced_and_are_correct()
