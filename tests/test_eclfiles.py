import os
from pathlib import Path

import pytest

from res2df import ResdataFiles

try:
    # pylint: disable=unused-import
    import opm  # noqa

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False

TESTDIR = Path(__file__).absolute().parent
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")


@pytest.mark.skipif(not HAVE_OPM, reason="OPM is not installed")
def test_filedescriptors():
    """Test that filedescriptors are properly closed"""
    # pylint: disable=protected-access

    fd_dir = Path("/proc/") / str(os.getpid()) / "fd"
    if not fd_dir.exists():
        print("Counting file descriptors on non-Linux not supported")
        return

    pre_fd_count = len(list(fd_dir.glob("*")))

    resdatafiles = ResdataFiles(EIGHTCELLS)
    # No opened files yet:
    assert len(list(fd_dir.glob("*"))) == pre_fd_count

    resdatafiles.close()
    # No change, no files to close:
    assert len(list(fd_dir.glob("*"))) == pre_fd_count

    resdatafiles.get_egrid()
    # This should not leave any file descriptor open
    assert len(list(fd_dir.glob("*"))) == pre_fd_count

    resdatafiles.get_initfile()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert resdatafiles._initfile is not None
    resdatafiles.close()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert resdatafiles._initfile is None

    resdatafiles.get_rstfile()
    # Automatically closed by resdata
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert resdatafiles._rstfile is not None
    resdatafiles.close()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert resdatafiles._rstfile is None

    resdatafiles.get_summary()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count + 1
    resdatafiles.close()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count

    resdatafiles.get_egridfile()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert resdatafiles._egridfile is not None
    resdatafiles.close()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert resdatafiles._egridfile is None

    resdatafiles.get_rftfile()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert resdatafiles._rftfile is not None
    resdatafiles.close()
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
    assert resdatafiles._rftfile is None

    resdatafiles.get_deck()
    # This should not leave any file descriptor open
    assert len(list(fd_dir.glob("*"))) == pre_fd_count
