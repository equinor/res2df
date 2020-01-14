#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract WCON* from an Eclipse deck

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import argparse
import logging
import datetime
import pandas as pd

from .eclfiles import EclFiles
from .common import parse_opmio_date_rec, parse_opmio_deckrecord

logging.basicConfig()
logger = logging.getLogger(__name__)

# The keywords supported in this module.
WCONKEYS = ["WCONHIST", "WCONINJE", "WCONINJH", "WCONPROD"]

# Rename some of the sunbeam columns:
COLUMN_RENAMER = {"VFPTable": "VFP_TABLE", "Lift": "ALQ"}


def deck2wcondf(deck):
    """Deprecated function name"""
    logger.warning("Deprecated function name, deck2wcondf")
    return deck2df(deck)


def deck2df(deck):
    """Loop through the deck and pick up information found

    The loop over the deck is a state machine, as it has to pick up dates

    Return:
        pd.DataFrame
    """
    wconrecords = []  # List of dicts of every line in input file
    date = None  # DATE columns will always be there, but can contain NaN
    for kword in deck:
        if kword.name == "DATES" or kword.name == "START":
            for rec in kword:
                date = parse_opmio_date_rec(rec)
                logger.info("Parsing at date %s", str(date))
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
                rec_data = {}
                rec_data = parse_opmio_deckrecord(rec, kword.name)
                rec_data["DATE"] = date
                rec_data["KEYWORD"] = kword.name

                for rec_key in RECORD_KEYS[kword.name]:
                    try:
                        if rec[rec_key]:
                            rec_data[rec_key.upper()] = rec[rec_key][0]
                    except ValueError:
                        pass
                wconrecords.append(rec_data)

        elif kword.name == "TSTEP":
            logger.warning("WARNING: Possible premature stop at first TSTEP")
            break

    wcon_df = pd.DataFrame(wconrecords)

    return wcon_df


def fill_parser(parser):
    """Set up sys.argv parsers.

    Arguments:
        parser (argparse.ArgumentParser or argparse.subparser): parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE", help="Name of Eclipse DATA file or Eclipse include file."
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Name of output csv file.", default="wcon.csv"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def main():
    """Entry-point for module, for command line utility
    """
    logger.warning("wcon2csv is deprecated, use 'ecl2csv wcon <args>' instead")
    parser = argparse.ArgumentParser()
    parser = fill_parser(parser)
    args = parser.parse_args()
    wcon2df_main(args)


def wcon2df_main(args):
    """Read from disk and write CSV back to disk"""
    if args.verbose:
        logger.setLevel(logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    wcon_df = deck2df(deck)
    if wcon_df.empty:
        logger.warning("Empty wcon dataframe being written to disk!")
    wcon_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)


def df(eclfiles):
    """Main function for Python API users"""
    return deck2df(eclfiles.get_ecldeck())
