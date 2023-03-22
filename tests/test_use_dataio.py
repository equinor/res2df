"""tests of function write_dframe_and_meta_to_file"""
from argparse import Namespace
from pathlib import Path
import pandas as pd
from ecl2df.common import write_dframe_and_meta_to_file

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
META_PATH = TESTDIR / "data/reek/fmuconfig/output/global_variables.yml"


def test_write_w_metadata():
    test = pd.DataFrame({"test": [1, 2, 3]})

    args = Namespace(DATAFILE=REEK, output="summary.csv", subcommand="summary")

    write_dframe_and_meta_to_file(test, META_PATH, args)
    share_folder = Path("share/results/tables")
    files = list(share_folder.glob("*summary"))
    assert len(files) == 2, "produced different to two files"
    share_folder.parent.parent.parent.unlink()
