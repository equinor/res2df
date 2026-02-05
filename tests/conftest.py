import logging
from pathlib import Path

import pytest

import res2df


@pytest.fixture
def path_to_res2df():
    """Path to installed res2df module"""
    return Path(res2df.__file__).parent


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """Clean up all logger handlers after each test
    to avoid messing up the loggers for subsequent tests.
    """
    yield
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        logger.handlers.clear()


def pytest_addoption(parser):
    parser.addoption(
        "--run-eclipse-simulator",
        action="store_true",
        default=False,
        help="Include tests that run the Eclipse reservoir simulator",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker("requires_eclipse") and not config.getoption(
            "--run-eclipse-simulator"
        ):
            item.add_marker(pytest.mark.skip("Requires eclipse"))
