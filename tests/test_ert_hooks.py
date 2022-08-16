import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest

import ecl2df
from ecl2df.hook_implementations import jobs

try:
    # pylint: disable=unused-import

    import ert.shared  # noqa

    HAVE_ERT = True
except ImportError:
    HAVE_ERT = False

TESTDIR = Path(__file__).absolute().parent
DATADIR = TESTDIR / "data/reek/eclipse/model"


@pytest.mark.skipif(
    not HAVE_ERT, reason="ERT is not installed, skipping hook implementation tests."
)
def test_ecl2csv_through_ert(tmp_path):
    """Test running the ERT executable on a mocked config file"""
    os.chdir(tmp_path)

    # Symlink Eclipse output to our tmp_path:
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


@pytest.mark.skipif(not HAVE_ERT, reason="ERT is not installed")
def test_job_documentation():
    if HAVE_ERT:
        assert (
            type(jobs.job_documentation("ECL2CSV"))
            == ert.shared.plugins.plugin_response.PluginResponse
        )
        assert (
            type(jobs.job_documentation("CSV2ECL"))
            == ert.shared.plugins.plugin_response.PluginResponse
        )
    else:
        assert jobs.job_documentation("ECL2CSV") is None
        assert jobs.job_documentation("CSV2ECL") is None

    assert jobs.job_documentation("foobar") is None


def test_get_module_variable():
    """Test that we can robustly peek into jobs for metadata.

    This is independent whether ERT is installed or not
    """
    assert jobs._get_module_variable_if_exists("foo", "bar") == ""
    assert jobs._get_module_variable_if_exists(
        "ecl2df.ecl2csv", "DESCRIPTION"
    ).startswith("Convert Eclipse input and output")
    assert jobs._get_module_variable_if_exists("ecl2df.ecl2csv", "NOPE") == ""


@pytest.mark.skipif(HAVE_ERT, reason="Tested only when ERT is not available")
def test_no_erthooks():
    """Test that we can import the hook implementations even when ERT is unavailable."""
    from ecl2df.hook_implementations import jobs  # noqa
