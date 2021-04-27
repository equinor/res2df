import subprocess
from pathlib import Path

import pandas as pd

import pytest

import ecl2df

try:
    # pylint: disable=unused-import

    import ert_shared  # noqa
except ImportError:
    pytest.skip(
        "ERT is not installed, skipping hook implementation tests.",
        allow_module_level=True,
    )


TESTDIR = Path(__file__).absolute().parent
DATADIR = TESTDIR / "data/reek/eclipse/model"


def test_ecl2csv_through_ert(tmpdir):
    """Test running the ERT executable on a mocked config file"""
    tmpdir.chdir()

    # Symlink Eclipse output to our tmpdir:
    eclbase = "2_R001_REEK-0"
    ecl_extensions = [
        "DATA",
        "ECLEND",
        "EGRID",
        "INIT",
        "PRT",
        "RFT",
        "SMSPEC",
        "UNRST",
        "UNSMRY",
    ]

    for ext in ecl_extensions:
        f_name = eclbase + "." + ext
        Path(f_name).symlink_to(DATADIR / f_name)

    ert_config = [
        "ECLBASE " + eclbase + ".DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH .",
    ]

    csv2ecl_subcommands = ["equil", "pvt", "satfunc"]

    for subcommand in ecl2df.SUBMODULES:
        ert_config.append(
            "FORWARD_MODEL ECL2CSV(<SUBCOMMAND>={0}, <OUTPUT>={0}.csv)".format(
                subcommand
            )
        )

    # Test what we can also supply additional options for some submodules:
    ert_config.append(
        "FORWARD_MODEL ECL2CSV(<SUBCOMMAND>=summary, "
        '<OUTPUT>=summary-yearly.csv, <XARG1>="--time_index", <XARG2>=yearly)'
    )
    ert_config.append(
        "FORWARD_MODEL ECL2CSV(<SUBCOMMAND>=equil, "
        '<OUTPUT>=equil-rsvd.csv, <XARG1>="--keywords", <XARG2>="RSVD")'
    )
    ert_config.append(
        "FORWARD_MODEL ECL2CSV(<SUBCOMMAND>=pvt, "
        '<OUTPUT>=pvt-custom.csv, <XARG1>="--keywords", <XARG2>="PVTO")'
    )
    ert_config.append(
        "FORWARD_MODEL ECL2CSV(<SUBCOMMAND>=satfunc, "
        '<OUTPUT>=satfunc-swof.csv, <XARG1>="--keywords", <XARG2>="SWOF")'
    )

    for subcommand in csv2ecl_subcommands:
        ert_config.append(
            "FORWARD_MODEL CSV2ECL("
            + "<SUBCOMMAND>={0}, <CSVFILE>={0}.csv, <OUTPUT>={0}.inc".format(subcommand)
            + ")"
        )
    ert_config.append(
        "FORWARD_MODEL CSV2ECL(<SUBCOMMAND>=summary, <CSVFILE>=summary-yearly.csv), "
        "<OUTPUT>=SUMYEARLY)"
    )

    ert_config_filename = "ecl2csv_test.ert"
    Path(ert_config_filename).write_text("\n".join(ert_config), encoding="utf-8")

    subprocess.call(["ert", "test_run", ert_config_filename])

    assert Path("OK").is_file()

    for subcommand in ecl2df.SUBMODULES:
        assert Path(subcommand + ".csv").is_file()

    # Check the custom output where options were supplied to the subcommands:
    assert len(pd.read_csv("summary-yearly.csv")) == 5
    assert set(pd.read_csv("equil-rsvd.csv")["KEYWORD"]) == set(["RSVD"])
    assert set(pd.read_csv("pvt-custom.csv")["KEYWORD"]) == set(["PVTO"])
    assert set(pd.read_csv("satfunc-swof.csv")["KEYWORD"]) == set(["SWOF"])

    for subcommand in csv2ecl_subcommands:
        assert Path(subcommand + ".inc").is_file()
