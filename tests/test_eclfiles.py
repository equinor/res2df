import os
from pathlib import Path

import pytest

from ecl2df import EclFiles

try:
    import opm  # noqa

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False


TESTDIR = Path(__file__).absolute().parent
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")


@pytest.mark.skipif(not HAVE_OPM, reason="OPM is not installed")
def test_filedescriptors():
    """Test that filedescriptors are properly closed"""

    fd_dir = Path("/proc/") / str(os.getpid()) / "fd"
    if not fd_dir.exists():
        print("Counting file descriptors on non-Linux not supported")
        return

    pre_fd_count = len(list(fd_dir.glob("*")))

    eclfiles = EclFiles(EIGHTCELLS)
    # No opened files yet:
    assert len(list(fd_dir.glob("*"))) == pre_fd_count

    eclfiles.close()
    # No change, no files to close:
    assert len(list(fd_dir.glob("*"))) == pre_fd_count

    eclfiles.get_egrid()
    # This should not leave any file descriptor open
    assert len(list(fd_dir.glob("*"))) == pre_fd_count

    eclfiles.get_initfile()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert eclfiles._initfile is not None
    eclfiles.close()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert eclfiles._initfile is None

    eclfiles.get_rstfile()
    # Automatically closed by libecl
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert eclfiles._rstfile is not None
    eclfiles.close()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert eclfiles._rstfile is None

    eclfiles.get_eclsum()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count + 1
    eclfiles.close()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count

    eclfiles.get_egridfile()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert eclfiles._egridfile is not None
    eclfiles.close()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert eclfiles._egridfile is None

    eclfiles.get_rftfile()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert eclfiles._rftfile is not None
    eclfiles.close()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert eclfiles._rftfile is None

    eclfiles.get_ecldeck()
    # This should not leave any file descriptor open
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
