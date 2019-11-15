#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract EQUIL from an Eclipse deck as Pandas DataFrame

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
import argparse
import pandas as pd

from ecl2df import inferdims
from .eclfiles import EclFiles


def deck2equildf(deck):
    """Deprecated function name"""
    logging.warning("Deprecated function name, deck2equildf")
    return deck2df(deck)


def deck2df(deck, ntequl=None):
    """Extract the data in the EQUIL keyword as a Pandas
    DataFrame.

    How each data value in the EQUIL records are to be interpreted
    depends on the phase configuration in the deck, which means
    that we need more than the EQUIL section alone to determine the
    dataframe.

    If ntequil is not supplied and EQLDIMS is not in the deck, the
    equil data is not well defined in terms of sunbeam. This means
    that we have to infer the correct number of EQUIL lines from what
    gives us successful parsing from sunbeam. In those cases, the
    deck must be supplied as a string, if not, extra EQUIL lines
    are possibly already removed by the sunbeam parser in eclfiles.str2deck().

    Arguments:
        deck (sunbeam.deck or str): Eclipse deck or string with deck. If
           not string, EQLDIMS must be present in the deck.
        ntequil (int): If not None, should state the NTEQUL in EQLDIMS. If
            None and EQLDIMS is not present, it will be inferred.

    Return:
        pd.DataFrame
    """
    if "EQLDIMS" not in deck:
        if not isinstance(deck, str):
            logging.critical(
                "Will not be able to guess NTEQUL from a parsed deck without EQLDIMS."
            )
            logging.critical(
                (
                    "Only data for the first EQUIL will be returned. "
                    "Instead, supply string to deck2df()"
                )
            )
            ntequl = 1
        if not ntequl:
            logging.warning("EQLDIMS+NTEQUL or ntequl not supplied. Will be guessed")
            ntequl_estimate = inferdims.guess_dim(deck, "EQLDIMS", 0)
            augmented_strdeck = inferdims.inject_dimcount(
                deck, "EQLDIMS", 0, ntequl_estimate
            )
            deck = EclFiles.str2deck(augmented_strdeck)
        else:
            augmented_strdeck = inferdims.inject_dimcount(deck, "EQLDIMS", 0, ntequl)
            deck = EclFiles.str2deck(augmented_strdeck)

    if isinstance(deck, str):
        deck = EclFiles.str2deck(deck)
    phasecount = sum(["OIL" in deck, "GAS" in deck, "WATER" in deck])
    if "OIL" in deck and "GAS" in deck and "WATER" in deck:
        # oil-water-gas
        columnnames = [
            "DATUM",
            "PRESSURE",
            "OWC",
            "PCOWC",
            "GOC",
            "PCGOC",
            "INITRS",
            "INITRV",
            "ACCURACY",
        ]
    if "OIL" not in deck and "GAS" in deck and "WATER" in deck:
        # gas-water
        columnnames = [
            "DATUM",
            "PRESSURE",
            "GWC",
            "PCGWC",
            "IGNORE1",
            "IGNORE2",
            "IGNORE3",
            "IGNORE4",
            "ACCURACY",
        ]
    if "OIL" in deck and "GAS" not in deck and "WATER" in deck:
        # oil-water
        columnnames = [
            "DATUM",
            "PRESSURE",
            "OWC",
            "PCOWC",
            "IGNORE1",
            "IGNORE2",
            "IGNORE3",
            "IGNORE4",
            "ACCURACY",
        ]
    if "OIL" in deck and "GAS" in deck and "WATER" not in deck:
        # oil-gas
        columnnames = [
            "DATUM",
            "PRESSURE",
            "IGNORE1",
            "IGNORE2",
            "GOC",
            "PCGOC",
            "IGNORE3",
            "IGNORE4",
            "ACCURACY",
        ]
    if phasecount == 1:
        columnnames = ["DATUM", "PRESSURE"]
    if not columnnames:
        raise ValueError("Unsupported phase configuration")

    if "EQUIL" not in deck:
        return pd.DataFrame

    records = []
    for rec in deck["EQUIL"]:
        rowlist = [x[0] for x in rec]
        if len(rowlist) > len(columnnames):
            rowlist = rowlist[: len(columnnames)]
            logging.warning(
                "Something wrong with columnnames " + "or EQUIL-data, data is chopped!"
            )
        records.append(rowlist)

    dataframe = pd.DataFrame(columns=columnnames, data=records)

    # The column handling can be made prettier..
    for col in dataframe.columns:
        if "IGNORE" in col:
            del dataframe[col]

    return dataframe


def fill_parser(parser):
    """Set up sys.argv parsers.

    Arguments:
        parser (argparse.ArgumentParser or argparse.subparser): parser to fill with arguments
    """
    parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument(
        "-o", "--output", type=str, help="Name of output csv file.", default="equil.csv"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def main():
    """Entry-point for module, for command line utility
    """
    logging.warning("equil2csv is deprecated, use 'ecl2csv equil <args>' instead")
    parser = argparse.ArgumentParser()
    parser = fill_parser(parser)
    args = parser.parse_args()
    equil2df_main(args)


def equil2df_main(args):
    """Read from disk and write CSV back to disk"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    equil_df = deck2df(deck)
    if equil_df.empty:
        logging.warning("Empty EQUIL-data being written to disk!")
    equil_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)


def df(eclfiles):
    """The "main" method for Python API users"""
    return deck2df(eclfiles.get_ecldeck())
