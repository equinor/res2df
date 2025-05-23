import itertools

import pytest

import res2df

from .test_grid import EIGHTCELLS, REEK

try:
    # pylint: disable=unused-import
    import opm  # noqa

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False


def test_default_logger_levels_and_split(capsys):
    """Verify that the intended usage of this logger have expected results"""

    splitlogger = res2df.getLogger_res2csv("test_levels_split")

    splitlogger.debug("This DEBUG-text is not to be seen")
    captured = capsys.readouterr()
    assert "DEBUG-text" not in captured.out
    assert "DEBUG-text" not in captured.err

    splitlogger.info("This INFO-text is not to be seen by default")
    captured = capsys.readouterr()
    assert "INFO-text" not in captured.out

    splitlogger.warning("This WARNING-text is to be seen in stdout")
    captured = capsys.readouterr()
    assert "WARNING-text" in captured.out
    assert "WARNING-text" not in captured.err

    splitlogger.error("This ERROR-text should only be in stderr")
    captured = capsys.readouterr()
    assert "ERROR-text" not in captured.out
    assert "ERROR-text" in captured.err

    # If output is written to stdout, all logs should go to stderr:
    nosplit_logger = res2df.getLogger_res2csv(
        "test_levels_nosplit", args_dict={"output": "-", "debug": True}
    )
    nosplit_logger.debug("This DEBUG-text is to be seen in stderr")
    captured = capsys.readouterr()
    assert "DEBUG-text" not in captured.out
    assert "DEBUG-text" in captured.err

    nosplit_logger.info("This INFO-text is to be seen by in stderr")
    captured = capsys.readouterr()
    assert "INFO-text" not in captured.out
    assert "INFO-text" in captured.err

    nosplit_logger.warning("This WARNING-text is to be seen in stderr")
    captured = capsys.readouterr()
    assert "WARNING-text" not in captured.out
    assert "WARNING-text" in captured.err

    nosplit_logger.error("This ERROR-text should only be in stderr")
    captured = capsys.readouterr()
    assert "ERROR-text" not in captured.out
    assert "ERROR-text" in captured.err


@pytest.mark.skipif(not HAVE_OPM, reason="Command line client requires OPM")
@pytest.mark.parametrize(
    "res2df_module, verbose, fileexport",
    itertools.product(res2df.SUBMODULES, [False, True], [True, False]),
)
def test_res2csv_logging(tmp_path, res2df_module, verbose, fileexport, mocker, capsys):
    """Test that the command line client for each submodule logs correctly.

    Each submodule should write logs to stdout for INFO and WARNING messages
    when they write to dedicated output files, but must write to stderr when
    stdout is used as the CSV output stream. This requres correct configuration
    in each submodule and must therefore be tested.

    This test function is more robust if each main() invocation is run in a
    subprocess, but that also makes it 10 times slower. When not run in a
    subprocess, the verbosity option must be False before True for the tests to
    work, this is related (?) to loggers not being properly reset between each
    test invocation.
    """
    # pylint: disable=too-many-arguments
    if res2df_module == "nnc":
        # There are no nnc's in EIGHTCELLS, so for that test
        # we need the REEK dataset:
        commands = ["res2csv", res2df_module, REEK, "--output"]
    else:
        commands = ["res2csv", res2df_module, EIGHTCELLS, "--output"]

    if fileexport:
        commands.append(str(tmp_path / "output.csv"))
    else:
        commands.append(res2df.common.MAGIC_STDOUT)

    if verbose:
        commands.append("-v")

    mocker.patch("sys.argv", commands)

    res2df.res2csv.main()
    captured = capsys.readouterr()
    stdout_output = captured.out
    stderr_output = captured.err

    if fileexport:
        if verbose:
            assert "INFO:" in stdout_output
            assert "INFO:" not in stderr_output
        else:
            assert "INFO:" not in stdout_output
            assert "INFO:" not in stderr_output
    elif verbose:
        assert "INFO:" in stderr_output
        assert "INFO:" not in stdout_output
    else:
        assert "INFO:" not in stdout_output
        assert "INFO:" not in stderr_output


def test_repeated_logger_construction(capsys):
    """If we repeatedly call getLogger(), ensure handlers are not added on top"""
    logger = res2df.getLogger_res2csv("nodouble")
    logger = res2df.getLogger_res2csv("nodouble")
    logger.warning("Don't repeat me")
    captured = capsys.readouterr()
    assert captured.out.count("Don't repeat me") == 1
