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

import sunbeam

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
    """Deprecated function, to be removed"""
    logging.warning("Deprecated function name, deck2satfuncdf")
    return deck2df(deck)


def inject_satnumcount(deckstr, satnumcount):
    """Insert a TABDIMS with NTSFUN into a deck

    This is simple string manipulation, not sunbeam
    deck manipulation (which might be possible to do).

    Arguments:
        deckstr (str): A string containing a partial deck (f.ex only
            the SWOF keyword).
        satnumcount (int): The NTSFUN number to use in TABDIMS
            (this function does not care if it is correct or not)
    Returns:
        str: New deck with TABDIMS prepended.
    """
    if "TABDIMS" in deckstr:
        logging.warning("Not inserting TABDIMS in a deck where already exists")
        return deckstr
    return "TABDIMS\n " + str(satnumcount) + " /\n\n" + str(deckstr)


def guess_satnumcount(deckstring):
    """Guess the SATNUM count for an incoming deck (string) without TABDIMS

    The incoming deck must in string form, if not, extra data is most
    likely already removed by the sunbeam parser.

    This function will inject TABDIMS into it and reparse it in a
    stricter mode, to detect the correct number of SATNUMs present

    Arguments:
        deck (str): String containing an Eclipse deck or only a few Eclipse keywords

    Returns:
        int: Inferred number of SATNUMs present

    """
    # Assert that TABDIMS is not present, we do not support the situation
    # where it is present and wrong.

    # A less than ecl2df-standard permissive sunbeam, when using
    # this one sunbeam will fail if there are extra records
    # in tables (if NTSFUN in TABDIMS is wrong f.ex):
    sunbeam_recovery_fail_extra_records = [
        ("PARSE_UNKNOWN_KEYWORD", sunbeam.action.ignore),
        ("SUMMARY_UNKNOWN_GROUP", sunbeam.action.ignore),
        ("UNSUPPORTED_*", sunbeam.action.ignore),
        ("PARSE_MISSING_SECTIONS", sunbeam.action.ignore),
        ("PARSE_RANDOM_TEXT", sunbeam.action.ignore),
        ("PARSE_MISSING_INCLUDE", sunbeam.action.ignore),
    ]

    max_guess = 640  # This ought to be enough for everybody
    for satnumcountguess in range(1, max_guess + 1):
        deck_candidate = inject_satnumcount(deckstring, satnumcountguess)
        try:
            EclFiles.str2deck(
                deck_candidate, recovery=sunbeam_recovery_fail_extra_records
            )
            # If we succeed, then the satnumcountguess was correct
            break
        except ValueError:
            # Typically we get the error PARSE_EXTRA_RECORDS because we did not guess
            # high enough satnumcount
            continue
            # If we get here, try another satnumcount
    if satnumcountguess == max_guess:
        logging.warning("Unable to guess satnums or larger than %d", max_guess)
    logging.info("Guessed satnumcount to %d", satnumcountguess)
    return satnumcountguess


def deck2df(deck, satnumcount=None):
    """Extract the data in the saturation function keywords as a Pandas
    DataFrame.

    Data for all saturation functions are merged into one dataframe.
    The two first columns in the dataframe are 'KEYWORD' (which can be
    SWOF, SGOF, etc.), and then SATNUM which is an index counter from 1 and
    onwards. Then follows the data for each individual keyword that
    is found in the deck.

    SATNUM data can only be parsed correctly if TABDIMS is present
    and stating how many saturation functions there should be.
    If you have a string with TABDIMS missing, you must supply
    this as a string to this function, and not a parsed deck, as
    the default parser in EclFiles is very permissive (and only
    returning the first function by default).

    Arguments:
        deck (sunbeam.deck or str): Incoming data deck. Always
            supply as a string if you don't know TABDIMS-NTSFUN.
        satnumcount (int): Number of SATNUMs defined in the deck, only
            needed if TABDIMS with NTSFUN is not found in the deck.
            If not supplied (or None) and NTSFUN is not defined,
            it will be attempted inferred.

    Return:
        pd.DataFrame, columns 'SW', 'KRW', 'KROW', 'PC', ..
    """
    if "TABDIMS" not in deck:
        if not isinstance(deck, str):
            logging.critical(
                "Will not be able to guess NTSFUN from a parsed deck without TABDIMS."
            )
            logging.critical(
                (
                    "Only data for first SATNUM will be returned."
                    "Instead, supply string to deck2df()"
                )
            )
            satnumcount = 1
        # If TABDIMS is in the deck, NTSFUN always has a value. It will
        # be set to 1 if defaulted.
        if not satnumcount:
            logging.warning(
                "TABDIMS+NTSFUN or satnumcount not supplied. Will be guessed."
            )
            ntsfun_estimate = guess_satnumcount(deck)
            augmented_strdeck = inject_satnumcount(str(deck), ntsfun_estimate)
            # Re-parse the modified deck:
            deck = EclFiles.str2deck(augmented_strdeck)

        else:
            augmented_strdeck = inject_satnumcount(str(deck), satnumcount)
            # Re-parse the modified deck:
            deck = EclFiles.str2deck(augmented_strdeck)

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
        parser (ArgumentParser or subparser): parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE", help="Name of Eclipse DATA file or file with saturation functions."
    )
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
    if "TABDIMS" in deck:
        # Things are easier when a full deck with correct TABDIMS
        # is supplied:
        satfunc_df = deck2df(deck)
    else:
        # When TABDIMS is not present, the code will try to infer
        # the number of saturation functions, this is necessarily
        # more error-prone:
        stringdeck = "".join(open(args.DATAFILE).readlines())
        satfunc_df = deck2df(stringdeck)
    logging.info(
        "Unique satnums: %d, saturation keywords: %s",
        satfunc_df["SATNUM"].unique(),
        satfunc_df["KEYWORD"].unique(),
    )
    satfunc_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)
