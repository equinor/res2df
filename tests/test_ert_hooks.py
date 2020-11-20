import subprocess
from pathlib import Path

import pytest

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
            "FORWARD_MODEL ECL2CSV(<SUBCOMMAND>={0}, <OUTPUT>={0}.csv)".format(
                subcommand
            )
        )
    for subcommand in csv2ecl_subcommands:
        ert_config.append(
            "FORWARD_MODEL CSV2ECL("
            + "<SUBCOMMAND>={0}, <CSVFILE>={0}.csv, <OUTPUT>={0}.inc".format(subcommand)
            + ")"
        )

    ert_config_filename = "ecl2csv_test.ert"
    Path(ert_config_filename).write_text("\n".join(ert_config), encoding="utf-8")

    subprocess.call(["ert", "test_run", ert_config_filename])

    assert Path("OK").is_file()

    for subcommand in ecl2csv_subcommands:
        assert Path(subcommand + ".csv").is_file()
    for subcommand in csv2ecl_subcommands:
        assert Path(subcommand + ".inc").is_file()
