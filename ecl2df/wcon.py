#!/usr/bin/env python
"""
Extract WCON* from an Eclipse deck

"""

import re
import logging
import datetime
import shlex

import pandas as pd

from .eclfiles import EclFiles
from .common import parse_opmio_date_rec, OPMKEYWORDS

logger = logging.getLogger(__name__)

# The keywords supported in this module.
WCONKEYS = ["WCONHIST", "WCONINJE", "WCONINJH", "WCONPROD"]

# Rename some of the opm-common column names:
COLUMN_RENAMER = {"VFPTable": "VFP_TABLE", "Lift": "ALQ"}


def unroll_defaulted_items(itemlist):
    """
    Expand list if list contains <int>* string elements

    so ['a', '2*', 'b'] becomes ['a', '1*', '1*', 'b']
    """
    multipledefaults_matcher = re.compile(r"(\d+)\*")
    unrolled_items = []
    for item in itemlist:
        def_matches = multipledefaults_matcher.match(item)
        if def_matches:
            unrolled_items.extend(["1*"] * int(def_matches.group(1)))
        else:
            unrolled_items.extend([item])
    return unrolled_items


def ad_hoc_wconparser(record, keyword):
    """This is a band-aid solution awaiting support for UDA-values in opm-common

    Replace this with common.parse_opmio_deckrecord when ready.

    Args:
        record (str): a string representation of a record with wcon data
        keyword (str): The E100 keyword this record is valid for.
    """
    assert isinstance(record, str)
    assert keyword in WCONKEYS  # Avoid using this function for too much else.
    rec_items = unroll_defaulted_items(shlex.split(record))
    meta_and_data = zip(OPMKEYWORDS[keyword]["items"], rec_items)
    rec_dict = {}
    for item in meta_and_data:
        if item[1] == "/":
            break
        itemname = item[0]["name"]
        if item[0]["value_type"].lower() in ["uda", "double"]:
            dataconv = float
        elif item[0]["value_type"].lower() in ["int"]:
            dataconv = int
        else:
            dataconv = str
        if itemname in COLUMN_RENAMER:
            itemname = COLUMN_RENAMER[itemname]
        if item[1] == "1*":
            if "default" in item[0]:
                rec_dict[itemname] = dataconv(item[0]["default"])
            else:
                rec_dict[itemname] = None
        else:
            rec_dict[itemname] = dataconv(item[1])
    return rec_dict


def df(deck):
    """Loop through the deck and pick up information found

    The loop over the deck is a state machine, as it has to pick up dates

    Args:
        deck (opm.io Deck) or EclFiles object

    Return:
        pd.DataFrame
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
                rec_data = ad_hoc_wconparser(str(rec), kword.name)
                rec_data["DATE"] = date
                rec_data["KEYWORD"] = kword.name
                wconrecords.append(rec_data)

        elif kword.name == "TSTEP":
            logger.warning("WARNING: Possible premature stop at first TSTEP")
            break

    wcon_df = pd.DataFrame(wconrecords)

    return wcon_df


def fill_parser(parser):
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


def wcon_main(args):
    """Read from disk and write CSV back to disk"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    wcon_df = df(deck)
    if wcon_df.empty:
        logger.warning("Empty wcon dataframe being written to disk!")
    wcon_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)
