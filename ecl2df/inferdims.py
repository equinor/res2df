# -*- coding: utf-8 -*-
"""
Support module for inferring EQLDIMS and TABDIMS from incomplete
Eclipse 100 decks (typically single include-files)
"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
import opm.io

from ecl2df import EclFiles

logging.basicConfig()
logger = logging.getLogger(__name__)


def guess_dim(deckstring, dimkeyword, dimitem=0):
    """Guess the correct dimension count for an incoming deck (string)

    The incoming deck must in string form, if not, extra data is most
    likely already removed by the opm.io parser. TABDIMS or EQLDIMS
    must not be present

    This function will inject TABDIMS or EQLDIMS into it and reparse it in a
    stricter mode, to detect the correct table dimensionality

    Arguments:
        deck (str): String containing an Eclipse deck or only a few Eclipse keywords
        dimkeyword (str): Either TABDIMS or EQLDIMS
        dimitem (int): The element number in TABDIMS/EQLDIMS to modify
    Returns:
        int: The lowest number for which stricter opm.io parsing succeeds

    """

    if dimkeyword not in ["TABDIMS", "EQLDIMS"]:
        raise ValueError("Only supports TABDIMS and EQLDIMS")
    if dimkeyword == "TABDIMS":
        if dimitem not in [0, 1]:
            raise ValueError("Only support item 0 and 1 in TABDIMS")
    if dimkeyword == "EQLDIMS":
        if dimitem not in [0]:
            raise ValueError("Only item 0 in EQLDIMS can be estimated")

    # A less than ecl2df-standard permissive opm.io, when using
    # this one opm.io will fail if there are extra records
    # in tables (if NTSFUN in TABDIMS is wrong f.ex):
    opmioparser_recovery_fail_extra_records = [
        ("PARSE_UNKNOWN_KEYWORD", opm.io.action.ignore),
        ("SUMMARY_UNKNOWN_GROUP", opm.io.action.ignore),
        ("UNSUPPORTED_*", opm.io.action.ignore),
        ("PARSE_MISSING_SECTIONS", opm.io.action.ignore),
        ("PARSE_RANDOM_TEXT", opm.io.action.ignore),
        ("PARSE_MISSING_INCLUDE", opm.io.action.ignore),
    ]

    max_guess = 640  # This ought to be enough for everybody
    dimcountguess = 0
    for dimcountguess in range(1, max_guess + 1):
        deck_candidate = inject_dimcount(deckstring, dimkeyword, dimitem, dimcountguess)
        try:
            EclFiles.str2deck(
                deck_candidate,
                parsecontext=opm.io.ParseContext(
                    opmioparser_recovery_fail_extra_records
                ),
            )
            # If we succeed, then the dimcountguess was correct
            break
        except ValueError:
            # Typically we get the error PARSE_EXTRA_RECORDS because we did not guess
            # high enough dimnumcount
            continue
            # If we get here, try another dimnumcount
    if dimcountguess == max_guess:
        logger.warning(
            "Unable to guess dim count for %s, or larger than %d", dimkeyword, max_guess
        )
    logger.info("Guessed dimension count count for %s to %d", dimkeyword, dimcountguess)
    return dimcountguess


def inject_dimcount(deckstr, dimkeyword, dimitem, dimvalue):
    """Insert a TABDIMS with NTSFUN into a deck

    This is simple string manipulation, not opm.io
    deck manipulation (which might be possible to do).

    Arguments:
        deckstr (str): A string containing a partial deck (f.ex only
            the SWOF keyword).
        dimkeyword (str): Either TABDIMS or EQLDIMS
        dimitem (int): Item 0 (NTSSFUN) or 1 (NTPVT) of TABDIMS, only 0 for EQLDIMS.
        dimvalue (int): The NTSFUN/NTPVT/NTEQUIL number to use
            (this function does not care if it is correct or not)
    Returns:
        str: New deck with TABDIMS/EQLDIMS prepended.
    """
    if dimkeyword not in ["TABDIMS", "EQLDIMS"]:
        raise ValueError("Only supports TABDIMS and EQLDIMS")
    if dimkeyword == "TABDIMS":
        if dimitem not in [0, 1]:
            raise ValueError("Only support item 0 and 1 in TABDIMS")
    if dimkeyword == "EQLDIMS":
        if dimitem not in [0]:
            raise ValueError("Only item 0 in EQLDIMS can be estimated")

    if dimkeyword in deckstr:
        logger.warning("Not inserting %s in a deck where already exists", dimkeyword)
        return deckstr
    return (
        dimkeyword
        + "\n "
        + int(dimitem) * "1* "
        + str(dimvalue)
        + " /\n\n"
        + str(deckstr)
    )
