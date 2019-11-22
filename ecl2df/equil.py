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
from .common import parse_opmio_deckrecord

logging.basicConfig()
logger = logging.getLogger(__name__)


def deck2equildf(deck):
    """Deprecated function name"""
    logger.warning("Deprecated function name, deck2equildf")
    return deck2df(deck)


def deck2df(deck, ntequl=None):
    """Extract the data in the EQUIL keyword as a Pandas
    DataFrame.

    How each data value in the EQUIL records are to be interpreted
    depends on the phase configuration in the deck, which means
    that we need more than the EQUIL section alone to determine the
    dataframe.

    If ntequil is not supplied and EQLDIMS is not in the deck, the
    equil data is not well defined in terms of OPM. This means
    that we have to infer the correct number of EQUIL lines from what
    gives us successful parsing from OPM. In those cases, the
    deck must be supplied as a string, if not, extra EQUIL lines
    are possibly already removed by the OPM parser in eclfiles.str2deck().

    Arguments:
        deck (opm.io deck or str): Eclipse deck or string with deck. If
           not string, EQLDIMS must be present in the deck.
        ntequil (int): If not None, should state the NTEQUL in EQLDIMS. If
            None and EQLDIMS is not present, it will be inferred.

    Return:
        pd.DataFrame
    """
    if "EQLDIMS" not in deck:
        if not isinstance(deck, str):
            logger.critical(
                "Will not be able to guess NTEQUL from a parsed deck without EQLDIMS."
            )
            logger.critical(
                (
                    "Only data for the first EQUIL will be returned. "
                    "Instead, supply string to deck2df()"
                )
            )
            ntequl = 1
        if not ntequl:
            logger.warning("EQLDIMS+NTEQUL or ntequl not supplied. Will be guessed")
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
        columnrenamer = {
            "DATUM_DEPTH": "DATUM",
            "DATUM_PRESSURE": "PRESSURE",
            "OWC": "OWC",
            "PC_OWC": "PCOWC",
            "GOC": "GOC",
            "PC_GOC": "PCGOC",
            "BLACK_OIL_INIT": "INITRS",
            "BLACK_OIL_INIT_WG": "INITRV",
            "OIP_INIT": "ACCURACY",
        }
    if "OIL" not in deck and "GAS" in deck and "WATER" in deck:
        # gas-water
        columnrenamer = {
            "DATUM_DEPTH": "DATUM",
            "DATUM_PRESSURE": "PRESSURE",
            "OWC": "GWC",
            "PC_OWC": "PCGWC",
            "GOC": "IGNORE1",
            "PC_GOC": "IGNORE2",
            "BLACK_OIL_INIT": "IGNORE3",
            "BLACK_OIL_INIT_WG": "IGNORE4",
            "OIP_INIT": "ACCURACY",
        }
    if "OIL" in deck and "GAS" not in deck and "WATER" in deck:
        # oil-water
        columnrenamer = {
            "DATUM_DEPTH": "DATUM",
            "DATUM_PRESSURE": "PRESSURE",
            "OWC": "OWC",
            "PC_OWC": "PCOWC",
            "GOC": "IGNORE1",
            "PC_GOC": "IGNORE2",
            "BLACK_OIL_INIT": "IGNORE3",
            "BLACK_OIL_INIT_WG": "IGNORE4",
            "OIP_INIT": "ACCURACY",
        }
    if "OIL" in deck and "GAS" in deck and "WATER" not in deck:
        # oil-gas
        columnrenamer = {
            "DATUM_DEPTH": "DATUM",
            "DATUM_PRESSURE": "PRESSURE",
            "OWC": "IGNORE1",
            "PC_OWC": "IGNORE2",
            "GOC": "GOC",
            "PC_GOC": "PCGOC",
            "BLACK_OIL_INIT": "IGNORE3",
            "BLACK_OIL_INIT_WG": "IGNORE4",
            "OIP_INIT": "ACCURACY",
        }
    if phasecount == 1:
        columnrenamer = {"DATUM_DEPTH": "DATUM", "DATUM_PRESSURE": "PRESSURE"}
    if not columnrenamer:
        raise ValueError("Unsupported phase configuration")

    if "EQUIL" not in deck:
        return pd.DataFrame

    records = []
    for rec in deck["EQUIL"]:
        equil_recdict = parse_opmio_deckrecord(rec, "EQUIL", renamer=columnrenamer)
        records.append(equil_recdict)

    dataframe = pd.DataFrame(data=records)

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
    logger.warning("equil2csv is deprecated, use 'ecl2csv equil <args>' instead")
    parser = argparse.ArgumentParser()
    parser = fill_parser(parser)
    args = parser.parse_args()
    equil2df_main(args)


def equil2df_main(args):
    """Read from disk and write CSV back to disk"""
    if args.verbose:
        logger.setLevel(logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    equil_df = deck2df(deck)
    if equil_df.empty:
        logger.warning("Empty EQUIL-data being written to disk!")
    equil_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)


def df(eclfiles):
    """The "main" method for Python API users"""
    return deck2df(eclfiles.get_ecldeck())
