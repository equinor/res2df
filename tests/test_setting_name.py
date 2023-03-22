"""Tests autosetting of file names
"""
from pathlib import Path
import pytest
from ecl2df import ecl2csv

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


@pytest.mark.integration
def test_summmary_name(mocker):
    """Test that the command line utility ecl2csv exports the right names"""
    tmp_path = Path().cwd()

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
        # assert len(file_names) == 1, "Produced more than one file"
        file_name = file_names[0]
        print(f" file name in test {file_name}")
        name, tagname = file_name.name.replace(file_name.suffix, "").split("--")
        file_name.unlink()
        print(name)
        print(tagname)
        assert name == "2_R001_REEK", f"{name} is not as planned"
        assert tagname == module_name, f"tag {tagname} not as planned"
