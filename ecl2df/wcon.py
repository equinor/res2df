"""Extract WCON* from an Eclipse deck"""

import logging
import datetime
import argparse
from typing import Union

import pandas as pd

try:
    # Needed for mypy

    # pylint: disable=unused-import
    import opm.io
except ImportError:
    pass

from ecl2df import EclFiles
from ecl2df.common import (
    parse_opmio_date_rec,
    parse_opmio_deckrecord,
    write_dframe_stdout_file,
)

logger = logging.getLogger(__name__)

# The keywords supported in this module.
WCONKEYS = ["WCONHIST", "WCONINJE", "WCONINJH", "WCONPROD"]


def df(deck: Union[EclFiles, "opm.libopmcommon_python.Deck"]) -> pd.DataFrame:
    """Loop through the deck and pick up information found

    The loop over the deck is a state machine, as it has to pick up dates
    """

    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()

    wconrecords = []  # List of dicts of every line in input file
    date = None  # DATE columns will always be there, but can contain NaN
    for kword in deck:
        if kword.name == "DATES" or kword.name == "START":
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
        "DATAFILE", help="Name of Eclipse DATA file or Eclipse include file."
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Name of output csv file.", default="wcon.csv"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def wcon_main(args) -> None:
    """Read from disk and write CSV back to disk"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    wcon_df = df(deck)
    if wcon_df.empty:
        logger.warning("Empty wcon dataframe being written to disk!")
        return
    write_dframe_stdout_file(
        wcon_df,
        args.output,
        index=False,
        caller_logger=logger,
        logstr="Wrote to {}".format(args.output),
    )
