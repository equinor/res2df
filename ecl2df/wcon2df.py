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
from .common import parse_ecl_month


# The record keys are all taken from the OPM source code:
# https://github.com/OPM/opm-common/blob/master/src/opm/parser/eclipse/share/keywords/000_Eclipse100/W/WCONHIST etc.

RECORD_KEYS = {}
RECORD_KEYS["WCONHIST"] = [
    "WELL",
    "STATUS",
    "CMODE",
    "ORAT",
    "WRAT",
    "VFPTable",
    "Lift",
    "THP",
    "BHP",
    "NGLRAT",
]  # Note that the non-all-uppercase names here will be renamed.

RECORD_KEYS["WCONINJE"] = [
    "WELL",
    "TYPE",
    "STATUS",
    "CMODE",
    "RATE",
    "RESV",
    "BHP",
    "THP",
    "VFP_TABLE",
    "VAPOIL_C",
    "GAS_STEAM_RATIO",
    "SURFACE_OIL_FRACTION",
    "SURFACE_WATER_FRACTION",
    "SURFACE_GAS_FRACTION",
    "OIL_STEAM_RATIO",
]

RECORD_KEYS["WCONINJH"] = [
    "WELL",
    "TYPE",
    "STATUS",
    "CMODE",
    "RATE",
    "RESV",
    "BHP",
    "THP",
    "VFP_TABLE",
    "VAPOIL_C",
    "GAS_STEAM_RATIO",
    "SURFACE_OIL_FRACTION",
    "SURFACE_WATER_FRACTION",
    "SURFACE_GAS_FRACTION",
    "OIL_STEAM_RATIO",
]


RECORD_KEYS["WCONPROD"] = [
    "WELL",
    "STATUS",
    "CMODE",
    "ORAT",
    "WRAT",
    "GRAT",
    "LRAT",
    "RESV",
    "BHP",
    "THP",
    "VFP_TABLE",
    "ALQ",
    "E300_ITEM13",
    "E300_ITEM14",
    "E300_ITEM15",
    "E300_ITEM16",
    "E300_ITEM17",
    "E300_ITEM18",
    "E300_ITEM19",
    "E300_ITEM20",
]

# Rename some of the sunbeam columns:
COLUMN_RENAMER = {"VFPTable": "VFP_TABLE", "Lift": "ALQ"}


def deck2wcondf(deck):
    logging.warning("Deprecated function name, deck2wcondf")
    return deck2df(deck)


def deck2df(deck):
    """Loop through the deck and pick up information found

    The loop over the deck is a state machine, as it has to pick up dates

    Return:
        pd.DataFrame
    """
    wconrecords = []  # List of dicts of every line in input file
    date = None  # DATE columns will always be there, but can contain NaN
    for kw in deck:
        if kw.name == "DATES" or kw.name == "START":
            for rec in kw:
                day = rec["DAY"][0]
                month = rec["MONTH"][0]
                year = rec["YEAR"][0]
                date = datetime.date(year=year, month=parse_ecl_month(month), day=day)
                logging.info("Parsing at date " + str(date))
        elif kw.name == "TSTEP":
            if not date:
                logging.critical("Can't use TSTEP when there is no start_date")
                return
            for rec in kw:
                steplist = rec[0]
                # Assuming not LAB units, then the unit is days.
                days = sum(steplist)
                date += datetime.timedelta(days=days)
                logging.info(
                    "Advancing {} days to {} through TSTEP".format(str(days), str(date))
                )
        elif kw.name in RECORD_KEYS:
            for rec in kw:  # Loop over the lines inside WCON* record
                rec_data = {}
                rec_data["DATE"] = date
                rec_data["KEYWORD"] = kw.name
                for rec_key in RECORD_KEYS[kw.name]:
                    try:
                        if rec[rec_key]:
                            rec_data[rec_key.upper()] = rec[rec_key][0]
                    except ValueError:
                        pass
                wconrecords.append(rec_data)

        elif kw.name == "TSTEP":
            logging.warning("WARNING: Possible premature stop at first TSTEP")
            break

    wcon_df = pd.DataFrame(wconrecords)

    return wcon_df


def parse_args():
    """Parse sys.argv using argparse"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "DATAFILE", help="Name of Eclipse DATA file or Eclipse include file."
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Name of output csv file.", default="wcon.csv"
    )
    return parser.parse_args()


def main():
    """Entry-point for module, for command line utility"""
    args = parse_args()
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    wcon_df = deck2df(deck)
    wcon_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)
