#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract saturation function data (SWOF, SGOF, SWFN, ...)
from an Eclipse deck as Pandas DataFrame

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
import argparse
import numpy as np
import pandas as pd

from .eclfiles import EclFiles

KEYWORD_COLUMNS = {
    "SWOF": ["SW", "KRW", "KROW", "PCOW"],
    "SGOF": ["SG", "KRG", "KROG", "PCOG"],
    "SWFN": ["SW", "KRW", "PCOW"],
    "SOFN": ["SW", "KRO"],
    "SGFN": ["SG", "KRG", "PCOG"],
    "SOF3": ["SO", "KROW", "KROG"],
    "SLGOF": ["SL", "KRG", "KROG", "PCOG"],
}


def deck2satfuncdf(deck):
    logging.warning("Deprecated function name, deck2satfuncdf")
    return deck2df(deck)


def deck2df(deck):
    """Extract the data in the saturation function keywords as a Pandas
    DataFrame.

    Data for all saturation functions are merged into one dataframe.
    The two first columns in the dataframe are 'KEYWORD' (which can be
    SWOF, SGOF, etc.), and then SATNUM which is an index counter from 1 and
    onwards. Then follows the data for each individual keyword that
    is found in the deck.

    Return:
        pd.DataFrame, columns 'SW', 'KRW', 'KROW', 'PC', ..
    """
    frames = []
    for keyword in KEYWORD_COLUMNS.keys():
        if keyword in deck:
            satnum = 1
            for deckrecord in deck[keyword]:
                # All data for an entire SATNUM is returned in one list
                data = np.array(deckrecord[0])
                # Split up into the correct number of columns
                column_count = len(KEYWORD_COLUMNS[keyword])
                if len(data) % column_count:
                    logging.error("Inconsistent data length or bug")
                    return
                satpoints = int(len(data) / column_count)
                df = pd.DataFrame(
                    columns=KEYWORD_COLUMNS[keyword],
                    data=data.reshape(satpoints, column_count),
                )
                df["SATNUM"] = satnum
                df["KEYWORD"] = keyword
                df = df[["KEYWORD", "SATNUM"] + KEYWORD_COLUMNS[keyword]]
                satnum += 1
                frames.append(df)

    return pd.concat(frames, axis=0, sort=False)


def fill_parser(parser):
    """Set up sys.argv parsers.

    Arguments:
        parser (argparse.ArgumentParser or argparse.subparser): parser to fill with arguments
    """
    parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file.",
        default="satfuncs.csv",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def main():
    """Entry-point for module, for command line utility
    """
    logging.warning("satfunc2csv is deprecated, use 'ecl2csv satfunc <args>' instead")
    parser = argparse.ArgumentParser()
    parser = fill_parser(parser)
    args = parser.parse_args()
    satfunc2df_main(args)


def satfunc2df_main(args):
    """Entry-point for module, for command line utility"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    satfunc_df = deck2df(deck)
    satfunc_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)
