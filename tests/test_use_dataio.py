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
CONFIG_PATH = TESTDIR / "data/reek/fmuconfig/output/global_variables.yml"


def _assert_string(string_to_assert, answer):
    """assert that string is equal to another string

    Args:
        string_to_assert (str): the string to check
        answer (str): the correct string
    """
    ass_string = f"{string_to_assert} should have been {answer}"
    assert string_to_assert == answer, ass_string


def _assert_metadata_are_produced_and_are_correct(tagname, correct_len=2):
    """Assert that two files are produced, and that metadata are correct"""
    share_folder = Path("share/")
    files = list(share_folder.glob("results/tables/*.*"))
    print(files)
    nr_files = len(files)
    len_str = f"Nr of files should be 2, but is {nr_files}"
    assert len(files) == correct_len, len_str
    for file_path in files:
        if file_path.name.startswith("."):
            meta = yaml_load(file_path)
            print(meta["data"])
            _assert_string(meta["data"]["name"], "2_R001_REEK")
            if tagname != "bulk":
                _assert_string(meta["data"]["tagname"], tagname)
            print(meta["data"]["spec"]["columns"])
            # _assert_string(meta["data"]["table_index"], ["DATE"])
        else:
            print(pd.read_csv(file_path).head())

    rmtree(share_folder)


def test_write_dframe_and_meta_to_file():
    """Test function write_dframe_and_meta_to_file"""
    test = pd.DataFrame({"DATE": [1, 2, 3], "FOPT": [0, 1, 2]})
    args = {
        "DATAFILE": REEK,
        "config_path": CONFIG_PATH,
        "output": "summary.csv",
        "subcommand": "summary",
    }

    write_dframe_and_meta_to_file(test, args)
    _assert_metadata_are_produced_and_are_correct("summary")


def test_write_through_summary_main():
    """Test summary main entry point"""

    ecl2df.summary.export_w_metadata(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("summary")


def test_write_through_satfunc_main():
    """Test summary main entry point"""

    ecl2df.satfunc.export_w_metadata(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("satfunc")


def test_write_through_rft_main():
    """Test summary main entry point"""

    ecl2df.rft.export_w_metadata(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("rft")


def test_write_through_pvt_main():
    """Test summary main entry point"""

    ecl2df.pvt.export_w_metadata(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("pvt")


def test_write_through_pillar_main():
    """Test summary main entry point"""

    ecl2df.pillars.export_w_metadata(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("pillars")


def test_write_through_nnc_main():
    """Test summary main entry point"""

    ecl2df.nnc.export_w_metadata(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("nnc")


def test_write_through_grid_main():
    """Test summary main entry point"""

    ecl2df.grid.export_w_metadata(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("grid")


def test_write_through_fipreports_main():
    """Test summary main entry point"""

    ecl2df.fipreports.export_w_metadata(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("fipreports")


def test_write_through_faults_main():
    """Test summary main entry point"""

    ecl2df.faults.export_w_metadata(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("faults")


def test_write_through_equil_main():
    """Test summary main entry point"""

    ecl2df.equil.export_w_metadata(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("equil")


def test_write_through_compdat_main():
    """Test summary main entry point"""

    ecl2df.compdat.export_w_metadata(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("compdat")


def test_bulk_upload():
    """Test bulk upload"""

    ecl2df.ecl2sumo_bulk.bulk_upload(REEK, CONFIG_PATH)
    _assert_metadata_are_produced_and_are_correct("bulk", 22)


def test_limiting_bulk_upload():
    """Test bulk upload with only one submodule"""

    ecl2df.ecl2sumo_bulk.bulk_upload(REEK, CONFIG_PATH, ["rft"])
    _assert_metadata_are_produced_and_are_correct("rft")
