import os
import subprocess
import time
from contextlib import nullcontext as does_not_raise
from pathlib import Path

import pytest

import res2df.summary
from res2df import ResdataFiles


@pytest.mark.requires_eclipse
@pytest.mark.parametrize(
    "history_case, history_is_abspath, eclipse_version, expectation",
    [
        pytest.param("EIGHTCELLS", False, "2023.1", does_not_raise()),
        pytest.param("EIGHTCELLS" * 7, False, "2023.1", does_not_raise()),
        pytest.param("EIGHTCELLS" * 7, False, "2021.3", does_not_raise()),
        pytest.param(
            "EIGHTCELLS" * 8,
            False,
            "2023.1",
            does_not_raise(),
            id="eclipse2023-supports-longer-than-72byte-smspec",
        ),
        pytest.param(
            "EIGHTCELLS" * 8,
            False,
            "2021.3",
            pytest.raises(AssertionError),
            id="eclipse2021-does-not-support-long-smspec-header",
        ),
        pytest.param(
            "EIGHTCELLS" * 13,
            False,
            "2023.1",
            pytest.raises(RuntimeError),
            id="more-than-132-chars-pr-line-in-DATA",
        ),
        pytest.param(
            "EIGHTCELLS",
            True,
            "2023.1",
            does_not_raise(),  # but can fail if the pytest tmp directory is very long
            id="absolute-path-for-history-reference",
        ),
        pytest.param(
            "EIGHTCELLS" * 7,
            True,
            "2023.1",
            pytest.raises(RuntimeError),
            id="more-than-132-chars-due-to-abspath",
        ),
    ],
)
def test_summary_restarts(
    history_case, history_is_abspath, eclipse_version, expectation, tmpdir
):
    os.chdir(tmpdir)
    (tmpdir / f"{history_case}.DATA").write_text(eightcells_deck(), encoding="utf-8")

    restartref = history_case if not history_is_abspath else str(tmpdir / history_case)
    if history_is_abspath:
        assert Path(restartref).is_absolute()
    (tmpdir / f"{history_case}_PRED.DATA").write_text(
        eightcells_deck(
            solution=f"RESTART\n'{restartref}' 2 /", extra_schedule="TSTEP\n 1/"
        ),
        encoding="utf-8",
    )
    with expectation:
        run_reservoir_simulator(eclipse_version, f"{history_case}.DATA")
        run_reservoir_simulator(eclipse_version, f"{history_case}_PRED.DATA")

        assert (
            len(
                res2df.summary.df(
                    ResdataFiles(f"{history_case}_PRED"), include_restart=False
                )
            )
            == 1
        )
        assert (
            len(
                res2df.summary.df(
                    ResdataFiles(f"{history_case}_PRED"), include_restart=True
                )
            )
            == 4
        )


def run_reservoir_simulator(
    simulator: str, eclipse_version: str, datafile: str
) -> None:
    command = ["runeclipse", "-i", "-v", eclipse_version, datafile]
    result = subprocess.run(  # pylint: disable=subprocess-run-check
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if (
        result.returncode != 0
        and "LICENSE FAILURE" in result.stdout.decode() + result.stderr.decode()
    ):
        print("Eclipse failed due to license server issues. Retrying in 30 seconds.")
        time.sleep(30)
        result = subprocess.run(  # pylint: disable=subprocess-run-check
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    if result.returncode != 0:
        if result.stdout:
            print(result.stdout.decode())
        if result.stderr:
            print(result.stderr.decode())
        raise RuntimeError(f"reservoir simulator failed in {os.getcwd()}")
    return None


def eightcells_deck(
    solution: str = "EQUIL\n100 100 50 /", extra_schedule: str = ""
) -> str:
    return f"""
RUNSPEC
DIMENS
  2 2 2 /
OIL
WATER
START
  1 'JAN' 2000 /
TABDIMS
  1 1 20 20 2 /
EQLDIMS
  1 /
WELLDIMS
  1 /
WSEGDIMS
  1 10 10 /
UNIFIN
UNIFOUT
GRID
NEWTRAN
COORD
    0   0   0     0   0 100
   50   0   0    50   0 100
  100   0   0   100   0 100
    0  50   0     0  50 100
   50  50   0    50  50 100
  100  50   0   100  50 100
    0 100   0     0 100 100
   50 100   0    50 100 100
  100 100   0   100 100 100
/
ZCORN
  16*0 16*50 16*50 16*100
/
PORO
  8*0.2
/
PERMX
  8*100.0
/
PERMY
  8*100.0
/
PERMZ
  8*100.0
/
GRIDFILE
  0 1
/
INIT
PROPS
SWOF
-- SW KRW KROW PC
  0.1 0 1 1
  1 1.0 0.0 0
/
DENSITY
  800 1000 1.2 /
PVTW
  1 1 0.0001 0.2 0.00001 /
PVDO
  10 1   1
  150 0.9 1 /
ROCK
  100 0.0001 /
FILLEPS
REGIONS
SATNUM
  8*1 /
EQLNUM
  8*1 /
SOLUTION
{solution}
RPTRST
  ALLPROPS/
SUMMARY
FOPR
FOPT
WOPT
/
WOPR
/
SCHEDULE
SKIPREST
WELSPECS
 OP1 OPS 1 1 50 OIL /
/
COMPDAT
  OP1 1 1 1 1 OPEN 1* 1* 0.15  /
/
WELSEGS
  OP1 5 5 1* INC /
   2 2 1 1 10 10  0.015 0.0001 /
/
COMPSEGS
 OP1 /
  1 1 1 1      10 10 Z /
/
WRFTPLT
 '*' YES YES YES  /
/
WCONPROD
 OP1 OPEN ORAT 50 /
/
TSTEP
  1 1 /
{extra_schedule}
"""
