import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest

import res2df
from res2df.hook_implementations import jobs

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
def test_res2csv_through_ert(tmp_path):
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

    csv2res_subcommands = ["equil", "pvt", "satfunc"]

    for subcommand in res2df.SUBMODULES:
        ert_config.append(
            f"FORWARD_MODEL RES2CSV(<SUBCOMMAND>={subcommand}, "
            f"<OUTPUT>={subcommand}.csv)"
        )

    # Test what we can also supply additional options for some submodules:
    ert_config.append(
        "FORWARD_MODEL RES2CSV(<SUBCOMMAND>=summary, "
        '<OUTPUT>=summary-yearly.csv, <XARG1>="--time_index", <XARG2>=yearly)'
    )
    ert_config.append(
        "FORWARD_MODEL RES2CSV(<SUBCOMMAND>=equil, "
        '<OUTPUT>=equil-rsvd.csv, <XARG1>="--keywords", <XARG2>="RSVD")'
    )
    ert_config.append(
        "FORWARD_MODEL RES2CSV(<SUBCOMMAND>=pvt, "
        '<OUTPUT>=pvt-custom.csv, <XARG1>="--keywords", <XARG2>="PVTO")'
    )
    ert_config.append(
        "FORWARD_MODEL RES2CSV(<SUBCOMMAND>=satfunc, "
        '<OUTPUT>=satfunc-swof.csv, <XARG1>="--keywords", <XARG2>="SWOF")'
    )

    for subcommand in csv2res_subcommands:
        ert_config.append(
            f"FORWARD_MODEL CSV2RES(<SUBCOMMAND>={subcommand}, "
            f"<CSVFILE>={subcommand}.csv, <OUTPUT>={subcommand}.inc)"
        )
    ert_config.append(
        "FORWARD_MODEL CSV2RES(<SUBCOMMAND>=summary, <CSVFILE>=summary-yearly.csv, "
        "<OUTPUT>=SUMYEARLY)"
    )

    ert_config_filename = "res2csv_test.ert"
    Path(ert_config_filename).write_text("\n".join(ert_config), encoding="utf-8")

    subprocess.call(["ert", "test_run", ert_config_filename])

    assert Path("OK").is_file()

    for subcommand in res2df.SUBMODULES:
        assert Path(subcommand + ".csv").is_file()

    # Check the custom output where options were supplied to the subcommands:
    assert len(pd.read_csv("summary-yearly.csv")) == 5
    assert set(pd.read_csv("equil-rsvd.csv")["KEYWORD"]) == set(["RSVD"])
    assert set(pd.read_csv("pvt-custom.csv")["KEYWORD"]) == set(["PVTO"])
    assert set(pd.read_csv("satfunc-swof.csv")["KEYWORD"]) == set(["SWOF"])

    for subcommand in csv2res_subcommands:
        assert Path(subcommand + ".inc").is_file()


@pytest.mark.skipif(not HAVE_ERT, reason="ERT is not installed")
def test_job_documentation():
    """Test that for registered ERT forward models the documentation is non-empty"""
    if HAVE_ERT:
        assert (
            type(jobs.job_documentation("RES2CSV"))
            == ert.shared.plugins.plugin_response.PluginResponse
        )
        assert (
            type(jobs.job_documentation("CSV2RES"))
            == ert.shared.plugins.plugin_response.PluginResponse
        )

    else:
        assert jobs.job_documentation("RES2CSV") is None
        assert jobs.job_documentation("CSV2RES") is None

    assert jobs.job_documentation("foobar") is None


def test_get_module_variable():
    """Test that we can robustly peek into jobs for metadata.

    This is independent whether ERT is installed or not
    """
    # pylint: disable=protected-access
    assert jobs._get_module_variable_if_exists("foo", "bar") == ""
    assert jobs._get_module_variable_if_exists(
        "res2df.res2csv", "DESCRIPTION"
    ).startswith("Convert reservoir simulator input and output")
    assert jobs._get_module_variable_if_exists("res2df.res2csv", "NOPE") == ""


@pytest.mark.skipif(HAVE_ERT, reason="Tested only when ERT is not available")
def test_no_erthooks():
    """Test that we can import the hook implementations even when ERT is unavailable."""
    # pylint: disable=redefined-outer-name, unused-import
    # pylint: disable=reimported, import-outside-toplevel
    from res2df.hook_implementations import jobs  # noqa
