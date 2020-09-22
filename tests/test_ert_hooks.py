import os
import sys
import subprocess

import pytest

try:
    import ert_shared  # noqa
except ImportError:
    pytest.skip(
        "ERT is not installed, skipping hook implementation tests.",
        allow_module_level=True,
    )


TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATADIR = os.path.join(TESTDIR, "data/reek/eclipse/model")


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_ecl2csv_through_ert(tmpdir):
    tmpdir.chdir()

    # Symlink Eclipse output to our tmpdir:
    eclbase = "2_R001_REEK-0"
    ecl_extensions = [
        "DATA",
        "ECLEND",
        "EGRID",
        "INIT",
        "RFT",
        "SMSPEC",
        "UNRST",
        "UNSMRY",
    ]

    for ext in ecl_extensions:
        f_name = eclbase + "." + ext
        os.symlink(os.path.join(DATADIR, f_name), f_name)

    ert_config = [
        "ECLBASE " + eclbase + ".DATA",
        "QUEUE_SYSTEM LOCAL",
        "NUM_REALIZATIONS 1",
        "RUNPATH .",
    ]

    ecl2csv_subcommands = [
        "compdat",
        "equil",
        "grid",
        "nnc",
        "pillars",
        "pvt",
        "rft",
        "satfunc",
        "summary",
    ]

    csv2ecl_subcommands = ["equil", "pvt", "satfunc"]

    for subcommand in ecl2csv_subcommands:
        ert_config.append(
            "FORWARD_MODEL ECL2CSV(<SUBCOMMAND>={}, <OUTPUT>={}.csv)".format(
                subcommand, subcommand
            )
        )
    for subcommand in csv2ecl_subcommands:
        ert_config.append(
            "FORWARD_MODEL CSV2ECL("
            + "<SUBCOMMAND>={}, <CSVFILE>={}.csv, <OUTPUT>={}.inc".format(
                subcommand, subcommand, subcommand
            )
            + ")"
        )

    ert_config_filename = "ecl2csv_test.ert"
    with open(ert_config_filename, "w") as file_h:
        file_h.write("\n".join(ert_config))

    subprocess.call(["ert", "test_run", ert_config_filename])

    assert os.path.exists("OK")

    for subcommand in ecl2csv_subcommands:
        assert os.path.exists(subcommand + ".csv")
    for subcommand in csv2ecl_subcommands:
        assert os.path.exists(subcommand + ".inc")
