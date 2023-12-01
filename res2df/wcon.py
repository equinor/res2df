"""Extract WCON* from a .DATA file"""

import argparse
import datetime
import logging
from typing import Union

import pandas as pd

try:
    # Needed for mypy

    # pylint: disable=unused-import
    import opm.io
except ImportError:
    pass

from .common import (
    parse_opmio_date_rec,
    parse_opmio_deckrecord,
    write_dframe_stdout_file,
)
from .res2csvlogger import getLogger_res2csv
from .resdatafiles import ResdataFiles

logger = logging.getLogger(__name__)

# The keywords supported in this module.
WCONKEYS = ["WCONHIST", "WCONINJE", "WCONINJH", "WCONPROD"]


def df(deck: Union[ResdataFiles, "opm.libopmcommon_python.Deck"]) -> pd.DataFrame:
    """Loop through the :term:`deck` and pick up information found

    The loop over the :term:`deck` is a state machine, as it has to pick up dates
    """

    if isinstance(deck, ResdataFiles):
        deck = deck.get_deck()

    wconrecords = []  # List of dicts of every line in input file
    date = None  # DATE columns will always be there, but can contain NaN
    for kword in deck:
        if kword.name in ["DATES", "START"]:
            for rec in kword:
                logger.info("Parsing at date %s", str(date))
                date = parse_opmio_date_rec(rec)
        elif kword.name == "TSTEP":
            if not date:
                logger.critical("Can't use TSTEP when there is no start_date")
                return pd.DataFrame()
            for rec in kword:
                steplist = rec[0].get_raw_data_list()
                # Assuming not LAB units, then the unit is days.
                days = sum(steplist)
                date += datetime.timedelta(days=days)
                logger.info(
                    "Advancing %s days to %s through TSTEP", str(days), str(date)
                )
        elif kword.name in WCONKEYS:
            for rec in kword:  # Loop over the lines inside WCON* record
                rec_data = parse_opmio_deckrecord(rec, kword.name)
                rec_data["DATE"] = date
                rec_data["KEYWORD"] = kword.name
                wconrecords.append(rec_data)

        elif kword.name == "TSTEP":
            logger.warning("WARNING: Possible premature stop at first TSTEP")
            break

    wcon_df = pd.DataFrame(wconrecords)

    return wcon_df


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser (argparse.ArgumentParser or argparse.subparser): parser to
            fill with arguments
    """
    parser.add_argument(
        "DATAFILE",
        help="Name of the .DATA input file or include file.",
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Name of output csv file.", default="wcon.csv"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def wcon_main(args) -> None:
    """Read from disk and write CSV back to disk"""
    logger = getLogger_res2csv(  # pylint: disable:redefined-outer_name
        __name__, vars(args)
    )
    resdatafiles = ResdataFiles(args.DATAFILE)
    if resdatafiles:
        deck = resdatafiles.get_deck()
    wcon_df = df(deck)
    write_dframe_stdout_file(
        wcon_df,
        args.output,
        index=False,
        caller_logger=logger,
        logstr=f"Wrote to {args.output}",
    )
