"""
Support module for inferring EQLDIMS and TABDIMS from incomplete
Eclipse 100 decks (typically single include-files)
"""

import logging
from typing import Dict, Optional, Union

try:
    import opm.io
except ImportError:
    # Let parts of ecl2df work without OPM:
    pass

from ecl2df import EclFiles

logger = logging.getLogger(__name__)

# Constants to use for pointing to positions in the xxxDIMS keyword
DIMS_POS: Dict[str, int] = dict(NTPVT=1, NTSFUN=0, NTEQUL=0)


def guess_dim(deckstring: str, dimkeyword: str, dimitem: int = 0) -> int:
    """Guess the correct dimension count for an incoming deck (string)

    The incoming deck must in string form, if not, extra data is most
    likely already removed by the opm.io parser. TABDIMS or EQLDIMS
    must not be present

    This function will inject TABDIMS or EQLDIMS into it and reparse it in a
    stricter mode, to detect the correct table dimensionality

    Arguments:
        deck: String containing an Eclipse deck or only a few Eclipse keywords
        dimkeyword: Either TABDIMS or EQLDIMS
        dimitem: The element number in TABDIMS/EQLDIMS to modify
    Returns:
        The lowest number for which stricter opm.io parsing succeeds

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
        ("PARSE_INVALID_KEYWORD_COMBINATION", opm.io.action.ignore),
        ("PARSE_MISSING_INCLUDE", opm.io.action.ignore),
        ("PARSE_MISSING_SECTIONS", opm.io.action.ignore),
        ("PARSE_RANDOM_TEXT", opm.io.action.ignore),
        ("PARSE_UNKNOWN_KEYWORD", opm.io.action.ignore),
        ("SUMMARY_UNKNOWN_GROUP", opm.io.action.ignore),
        ("UNSUPPORTED_*", opm.io.action.ignore),
    ]

    max_guess = 640  # This ought to be enough for everybody
    dimcountguess = 0
    for dimcountguess in range(1, max_guess + 1):
        deck_candidate = inject_dimcount(
            deckstring, dimkeyword, dimitem, dimcountguess, nowarn=True
        )
        try:
            EclFiles.str2deck(
                deck_candidate,
                parsecontext=opm.io.ParseContext(
                    opmioparser_recovery_fail_extra_records
                ),
            )
            # If we succeed, then the dimcountguess was correct
            break
        except (ValueError, RuntimeError):
            # ValueError in opm-common <= 2020.04
            # RuntimeError in opm-common >= 2020.10
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


def inject_dimcount(
    deckstr: str, dimkeyword: str, dimitem: int, dimvalue: int, nowarn: bool = False
) -> str:
    """Insert a TABDIMS with NTSFUN into a deck

    This is simple string manipulation, not opm.io
    deck manipulation (which might be possible to do).

    This function is to be wrapped by inject_xxxdims_ntxxx()

    Arguments:
        deckstr: A string containing a partial deck (f.ex only
            the SWOF keyword).
        dimkeyword: Either TABDIMS or EQLDIMS
        dimitem: Item 0 (NTSSFUN) or 1 (NTPVT) of TABDIMS, only 0 for EQLDIMS.
        dimvalue: The NTSFUN/NTPVT/NTEQUIL number to use
            (this function does not care if it is correct or not but
            it must be larger than zero)
        nowarn: By default it will warn if this function
            is run on a deckstr with TABDIMS/EQLDIMS present. Mute this if True.
    Returns:
        New deck with TABDIMS/EQLDIMS prepended.
    """
    assert dimvalue > 0, "dimvalue must be larger than zero"
    if dimkeyword not in ["TABDIMS", "EQLDIMS"]:
        raise ValueError("Only supports TABDIMS and EQLDIMS")
    if dimkeyword == "TABDIMS":
        if dimitem not in [0, 1]:
            raise ValueError("Only support item 0 and 1 in TABDIMS")
    if dimkeyword == "EQLDIMS":
        if dimitem not in [0]:
            raise ValueError("Only item 0 in EQLDIMS can be injected")

    if dimkeyword in deckstr:
        if not nowarn:
            logger.warning(
                "Not inserting %s in a deck where already exists", dimkeyword
            )
        return deckstr
    return (
        dimkeyword
        + "\n "
        + int(dimitem) * "1* "
        + str(dimvalue)
        + " /\n\n"
        + str(deckstr)
    )


def inject_xxxdims_ntxxx(
    xxxdims: str,
    ntxxx_name: str,
    deck: Union[str, "opm.libopmcommon_python.Deck"],
    ntxxx_value: Optional[int] = None,
) -> "opm.libopmcommon_python.Deck":
    """Ensures TABDIMS/EQLDIMS is present in a deck.

    If ntxxx_value=None and ntxxx_name not in the deck, ntxxx_name will
    be inferred through trial-and-error parsing of the deck, and then injected
    into the deck.

    Args:
        xxxdims: TABDIMS or EQLDIMS
        ntxxx_name: NTPVT, NTEQUL or NTSFUN
        deck: A data deck. If ntxxx_name is to be
            estimated this *must* be a string and not a fully parsed deck.
        npxxx_value: Supply this if ntxxx_name is known, but not present in the
            deck, this will override any guessing. If the deck already
            contains XXXDIMS, this will be ignored.

    Returns:
        opm.io Deck object
    """
    assert xxxdims in ["TABDIMS", "EQLDIMS"]
    assert ntxxx_name in ["NTPVT", "NTEQUL", "NTSFUN"]

    if xxxdims in deck and ntxxx_value is None:
        # Then we have nothing to do, but ensure we parse a potential string to a deck
        if isinstance(deck, str):
            deck = EclFiles.str2deck(deck)
        return deck

    if xxxdims in deck and ntxxx_value is not None:
        logger.warning(
            "Ignoring %s argument, it is already in the deck", str(ntxxx_name)
        )
        return deck

    if not isinstance(deck, str):
        # The deck must be converted to a string deck in order
        # to estimate dimensions.
        deck = str(deck)

    # Estimate if ntxxx_value is not provided:
    if ntxxx_value is None:
        ntxxx_estimate = guess_dim(deck, xxxdims, DIMS_POS[ntxxx_name])
        logger.warning("Estimated %s=%s", ntxxx_name, str(ntxxx_estimate))
    else:
        ntxxx_estimate = ntxxx_value

    augmented_strdeck = inject_dimcount(
        str(deck), xxxdims, DIMS_POS[ntxxx_name], ntxxx_estimate, nowarn=True
    )
    # Overwrite the deck object
    deck = EclFiles.str2deck(augmented_strdeck)

    return deck
