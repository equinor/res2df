#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract saturation function data (SWOF, SGOF, SWFN, etc.)
from an Eclipse deck as Pandas DataFrame.

Data can be extracted from a full Eclipse deck (*.DATA)
or from individual files.

Note that when parsing from individual files, it is
undefined in the syntax how many saturation functions (SATNUMs) are
present. For convenience, it is possible to estimate the count of
SATNUMs, but whenever this is known, it is recommended to either supply
TABDIMS or to supply the satnumcount directly to avoid possible bugs.

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
import argparse
import numpy as np
import pandas as pd

from ecl2df import inferdims, common
from .eclfiles import EclFiles

logging.basicConfig()
logger = logging.getLogger(__name__)

SUPPORTED_KEYWORDS = ["SWOF", "SGOF", "SGWFN", "SWFN", "SOF2", "SGFN", "SOF3", "SLGOF"]

RENAMERS = {}
RENAMERS["SGFN"] = {"DATA": ["SG", "KRG", "PCOG"]}
RENAMERS["SGOF"] = {"DATA": ["SG", "KRG", "KROG", "PCOG"]}
RENAMERS["SGWFN"] = {"DATA": ["SG", "KRG", "KRW", "PCGW"]}
RENAMERS["SLGOF"] = {"DATA": ["SL", "KRG", "KRO", "PCOG"]}
RENAMERS["SOF2"] = {"DATA": ["SO", "KRO"]}
RENAMERS["SOF3"] = {"DATA": ["SO", "KROW", "KROG"]}
RENAMERS["SWFN"] = {"DATA": ["SW", "KRW", "PCOW"]}
RENAMERS["SWOF"] = {"DATA": ["SW", "KRW", "KROW", "PCOW"]}


def xx_inject_satnumcount(deckstr, satnumcount):
    """Insert a TABDIMS with NTSFUN into a deck

    This is simple string manipulation, not OPM
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
        logger.warning("Not inserting TABDIMS in a deck where already exists")
        return deckstr
    return "TABDIMS\n " + str(satnumcount) + " /\n\n" + str(deckstr)


def df(deck, keywords=None, ntsfun=None):
    """Extract the data in the saturation function keywords as a Pandas
    DataFrames.

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
        deck (opm.io deck or str): Incoming data deck. Always
            supply as a string if you don't know TABDIMS-NTSFUN.
        keywords (list of str): Requested keywords for which to
            to extract data.
        ntsfun (int): Number of SATNUMs defined in the deck, only
            needed if TABDIMS with NTSFUN is not found in the deck.
            If not supplied (or None) and NTSFUN is not defined,
            it will be attempted inferred.

    Return:
        pd.DataFrame, columns 'KEYWORD', 'SW', 'KRW', 'KROW', 'PC', ..
    """
    if isinstance(deck, EclFiles):
        # NB: If this is done on include files and not on DATA files
        # we can loose data for SATNUM > 1
        deck = deck.get_ecldeck()
    deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    assert "TABDIMS" in deck
    ntsfun = deck["TABDIMS"][0][inferdims.DIMS_POS["NTSFUN"]].get_int(0)

    keywords = common.handle_wanted_keywords(keywords, deck, SUPPORTED_KEYWORDS)

    frames = []
    for keyword in keywords:
        # Construct the associated function names
        function_name = keyword.lower() + "_fromdeck"
        function = globals()[function_name]
        dframe = function(deck, ntsfun=ntsfun)
        frames.append(dframe.assign(KEYWORD=keyword))
    nonempty_frames = [frame for frame in frames if not frame.empty]
    if nonempty_frames:
        return pd.concat(nonempty_frames, axis=0, sort=False, ignore_index=True)
    return pd.DataFrame()


def swof_fromdeck(deck, ntsfun=None):
    """Extract SWOF data from a deck

    Args:
        deck (str or opm.common Deck)
        ntsfun (int): Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SWOF", renamer=RENAMERS["SWOF"], recordcountername="SATNUM"
    )


def sgof_fromdeck(deck, ntsfun=None):
    """Extract SGOF data from a deck

    Args:
        deck (str or opm.common Deck)
        ntsfun (int): Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SGOF", renamer=RENAMERS["SGOF"], recordcountername="SATNUM"
    )


def swfn_fromdeck(deck, ntsfun=None):
    """Extract SWFN data from a deck

    Args:
        deck (str or opm.common Deck)
        ntsfun (int): Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SWFN", renamer=RENAMERS["SWFN"], recordcountername="SATNUM"
    )


def sof2_fromdeck(deck, ntsfun=None):
    """Extract SOF2 data from a deck

    Args:
        deck (str or opm.common Deck)
        ntsfun (int): Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SOF2", renamer=RENAMERS["SOF2"], recordcountername="SATNUM"
    )


def sgfn_fromdeck(deck, ntsfun=None):
    """Extract SGFN data from a deck

    Args:
        deck (str or opm.common Deck)
        ntsfun (int): Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SGFN", renamer=RENAMERS["SGFN"], recordcountername="SATNUM"
    )

def sgwfn_fromdeck(deck, ntsfun=None):
    """Extract SGWFN data from a deck

    Args:
        deck (str or opm.common Deck)
        ntsfun (int): Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SGWFN", renamer=RENAMERS["SGWFN"], recordcountername="SATNUM"
    )


def sof3_fromdeck(deck, ntsfun=None):
    """Extract SOF3 data from a deck

    Args:
        deck (str or opm.common Deck)
        ntsfun (int): Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SOF3", renamer=RENAMERS["SOF3"], recordcountername="SATNUM"
    )


def slgof_fromdeck(deck, ntsfun=None):
    """Extract SLGOF data from a deck

    Args:
        deck (str or opm.common Deck)
        ntsfun (int): Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SLGOF", renamer=RENAMERS["SLGOF"], recordcountername="SATNUM"
    )


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
    logger.warning("satfunc2csv is deprecated, use 'ecl2csv satfunc <args>' instead")
    parser = argparse.ArgumentParser()
    parser = fill_parser(parser)
    args = parser.parse_args()
    satfunc_main(args)


def satfunc_main(args):
    """Entry-point for module, for command line utility"""
    if args.verbose:
        logger.setLevel(logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    if "TABDIMS" in deck:
        # Things are easier when a full deck with (correct) TABDIMS
        # is supplied:
        satfunc_df = df(eclfiles)
    else:
        # This might be an include file for which we have to infer/guess
        # TABDIMS. Then we send it to df() as a string
        satfunc_df = df("".join(open(args.DATAFILE).readlines()))
    if not satfunc_df.empty:
        logger.info(
            "Unique satnums: %d, saturation keywords: %s",
            len(satfunc_df["SATNUM"].unique()),
            str(satfunc_df["KEYWORD"].unique()),
        )
    else:
        logger.warning("Empty saturation function dataframe being written to disk!")
    satfunc_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)


def deck2df(eclfiles):
    """Deprecated Python API"""
    return df(eclfiles)
