#!/usr/bin/env python
"""
Extract the contents of the FAULTS keyword into
a DataFrame

"""
import logging
import pandas as pd

from .eclfiles import EclFiles
from .common import parse_opmio_deckrecord, write_dframe_stdout_file

logger = logging.getLogger(__name__)

RECORD_COLUMNS = ["NAME", "IX1", "IX2", "IY1", "IY2", "IZ1", "IZ2", "FACE"]
COLUMNS = ["NAME", "I", "J", "K", "FACE"]
ALLOWED_FACES = ["X", "Y", "Z", "I", "J", "K", "X-", "Y-", "Z-", "I-", "J-", "K-"]


def df(deck):
    """Produce a dataframe of fault data from a deck

    All data for the keyword FAULTS will be returned.

    Args:
        deck (opm.io Deck or EclFiles): Eclipse deck
    """
    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()

    # In[91]: list(deck['FAULTS'][0])
    # Out[91]: [[u'F1'], [36], [36], [41], [42], [1], [14], [u'I']]
    data = []
    # It is allowed in Eclipse to use the keyword FAULTS
    # as many times as needed. Thus we need to loop in some way:
    for keyword in deck:
        if keyword.name == "FAULTS":
            for rec in keyword:
                # Each record now has a range potentially in three
                # dimensions for the fault, unroll this:
                frec_dict = parse_opmio_deckrecord(rec, "FAULTS")
                faultname = frec_dict["NAME"]
                faultface = frec_dict["FACE"]
                for i_idx in range(frec_dict["IX1"], frec_dict["IX2"] + 1):
                    for j_idx in range(frec_dict["IY1"], frec_dict["IY2"] + 1):
                        for k_idx in range(frec_dict["IZ1"], frec_dict["IZ2"] + 1):
                            data.append([faultname, i_idx, j_idx, k_idx, faultface])
    return pd.DataFrame(columns=COLUMNS, data=data)


def fill_parser(parser):
    """Set up sys.argv parsers.

    Arguments:
        parser: argparse.ArgumentParser or argparse.subparser
    """
    parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file.",
        default="faults.csv",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def faults_main(args):
    """Read from disk and write CSV back to disk"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    faults_df = df(deck)
    if faults_df.empty:
        logger.warning("Empty FAULT data, not written to disk!")
        return
    write_dframe_stdout_file(
        faults_df,
        args.output,
        index=False,
        caller_logger=logger,
        logstr="Wrote to {}".format(args.output),
    )
