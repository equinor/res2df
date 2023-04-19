from pathlib import Path
import pandas as pd
from ecl2df.ecl2sumo_bulk import bulk_upload


TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
META_PATH = TESTDIR / "data/reek/fmuconfig/output/global_variables.yml"
SHARE = Path("share/results/tables/")


def test_the_bulk_upload():
    """Test the upload of all types"""
    bulk_upload(REEK, META_PATH)
    for obj_path in SHARE.glob("[!.]*.csv"):
        print(obj_path)
        meta_path = obj_path.parent / ("." + obj_path.name + ".yml")
        assert meta_path.exists()
        results = pd.read_csv(obj_path)
        assert not results.empty
