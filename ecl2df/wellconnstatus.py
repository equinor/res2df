"""Exctracts connection status history for each well connections"""

import argparse
import logging
import re
from typing import Any, List, Tuple

import numpy as np
import pandas as pd

from ecl2df import getLogger_ecl2csv, summary
from ecl2df.eclfiles import EclFiles

from .common import write_dframe_stdout_file

logger = logging.getLogger(__name__)


def df(eclfiles: EclFiles) -> pd.DataFrame:
    """Exctracts connection status history for each compdat connection that
    is included in the summary data on the form CPI:WELL,I,J,K. CPI stands for
    connection productivity index.

    One line is added to the export every time a connection changes status. It
    is OPEN when CPI>0 and SHUT when CPI=0. The earliest date for any connection
    will be OPEN, i.e a cell can not be SHUT before it has been OPEN. This means
    that any cells that are always SHUT will be excluded.

    The output data set is very sparse compared to the CPI summary data.
    """
    smry = summary.df(eclfiles, column_keys="CPI*")
    return _extract_status_changes(smry)


def _extract_status_changes(smry: pd.DataFrame) -> pd.DataFrame:
    """Extracts connections status changes from a dataframe of CPI
    summary data.
    """
    cpi_columns = [
        col
        for col in smry.columns
        if re.match("^CPI:[A-Z0-9_-]{1,8}:[0-9]+,[0-9]+,[0-9]+$", col)
    ]
    dframe = pd.DataFrame(columns=["DATE", "WELL", "I", "J", "K", "OP/SH"])

    for col in cpi_columns:
        colsplit = col.split(":")
        well = colsplit[1]
        i, j, k = colsplit[2].split(",")

        status_changes = _extract_single_connection_status_changes(
            smry.index, smry[col]
        )
        for date, status in status_changes:
            dframe.loc[dframe.shape[0]] = [date, well, i, j, k, status]

    dframe["I"] = dframe["I"].astype(int)
    dframe["J"] = dframe["J"].astype(int)
    dframe["K"] = dframe["K"].astype(int)

    logger.info(
        "Dataframe with well connection status ready, %d rows",
        len(dframe),
    )
    return dframe


def _extract_single_connection_status_changes(
    dates: np.ndarray, conn_values: np.ndarray
) -> List[Tuple[Any, str]]:
    """Extracts the status history of a single connection as a list of tuples
    on the form (date, status)

    A CPI value of 0 means that the connection is SHUT
    A CPI value > 0 means that the connection is OPEN
    """
    status_changes = []
    prev_value = 0
    for date, value in zip(dates, conn_values):
        if value > 0 and prev_value == 0:
            # Connection is OPEN and was SHUT at previous timestep
            status_changes.append((date, "OPEN"))
        elif prev_value > 0 and value == 0:
            # Connection is SHUT and was OPEN at previous timestep
            status_changes.append((date, "SHUT"))
        prev_value = value
    return status_changes


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser: parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE",
        type=str,
        help="Name of Eclipse DATA file. " + "UNSMRY file must lie alongside.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=(
            "Name of output csv file. Use '-' to write to stdout. "
            "Default 'well_connection_status.csv'"
        ),
        default="well_connection_status.csv",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def wellconnstatus_main(args):
    """Entry-point for module, for command line utility"""
    logger = getLogger_ecl2csv(__name__, vars(args))
    eclfiles = EclFiles(args.DATAFILE)

    wellconnstatus_df = df(eclfiles)
    write_dframe_stdout_file(
        wellconnstatus_df, args.output, index=False, caller_logger=logger
    )
