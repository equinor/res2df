# -*- coding: utf-8 -*-
"""
Extract COMPDAT, WELSEGS and COMPSEGS from an Eclipse deck

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import argparse
import datetime
import logging
import pandas as pd

from .eclfiles import EclFiles
from .common import (
    merge_zones,
    parse_opmio_deckrecord,
    parse_opmio_date_rec,
    parse_opmio_tstep_rec,
)
from .grid import merge_initvectors

logging.basicConfig()
logger = logging.getLogger(__name__)

"""OPM authors and Roxar RMS authors have interpreted the Eclipse
documentation ever so slightly different when naming the data.

For COMPDAT dataframe columnnames, we prefer the RMS terms due to the
one very long one, and mixed-case in opm
"""
COMPDAT_RENAMER = {
    "WELL": "WELL",
    "I": "I",
    "J": "J",
    "K1": "K1",
    "K2": "K2",
    "STATE": "OP/SH",
    "SAT_TABLE": "SATN",
    "CONNECTION_TRANSMISSIBILITY_FACTOR": "TRAN",
    "DIAMETER": "WBDIA",
    "Kh": "KH",
    "SKIN": "SKIN",
    "D_FACTOR": "DFACT",
    "DIR": "DIR",
    "PR": "PEQVR",
}


def deck2compdatsegsdfs(deck, start_date=None):
    """Deprecated function name"""
    logger.warning("Deprecated method name: deck2compdatsegsdfs(), use deck2dfs()")
    return deck2dfs(deck, start_date)


def deck2dfs(deck, start_date=None, unroll=True):
    """Loop through the deck and pick up information found

    The loop over the deck is a state machine, as it has to pick up dates

    Args:
        deck (opm.libopmcommon_python.Deck): A deck representing the schedule
            Does not have to be a full Eclipse deck, an include file is sufficient
        start_date (datetime.date or str): The default date to use for
            events where the DATE or START keyword is not found in advance.
            Default: None
        unroll (bool): Whether to unroll rows that cover a range,
            like K1 and K2 in COMPDAT and in WELSEGS. Defaults to True.

    Returns:
        Dictionary with 3 dataframes, named COMPDAT, COMPSEGS and WELSEGS.
    """
    compdatrecords = []  # List of dicts of every line in input file
    compsegsrecords = []
    welsegsrecords = []
    date = start_date  # DATE column will always be there, but can contain NaN/None
    for kword in deck:
        if kword.name == "DATES" or kword.name == "START":
            for rec in kword:
                date = parse_opmio_date_rec(rec)
                logger.info("Parsing at date %s", str(date))
        elif kword.name == "TSTEP":
            if not date:
                logger.critical("Can't use TSTEP when there is no start_date")
                return {}
            for rec in kword:
                steplist = parse_opmio_tstep_rec(rec)
                # Assuming not LAB units, then the unit is days.
                days = sum(steplist)
                date += datetime.timedelta(days=days)
                logger.info(
                    "Advancing %s days to %s through TSTEP", str(days), str(date)
                )
        elif kword.name == "COMPDAT":
            for rec in kword:  # Loop over the lines inside COMPDAT record
                rec_data = parse_opmio_deckrecord(
                    rec, "COMPDAT", renamer=COMPDAT_RENAMER
                )
                rec_data["DATE"] = date
                compdatrecords.append(rec_data)
        elif kword.name == "COMPSEGS":
            wellname = parse_opmio_deckrecord(
                kword[0], "COMPSEGS", itemlistname="records", recordindex=0
            )["WELL"]
            for recidx in range(1, len(kword)):
                rec = kword[recidx]
                rec_data = parse_opmio_deckrecord(
                    rec, "COMPSEGS", itemlistname="records", recordindex=1
                )
                rec_data["WELL"] = wellname
                rec_data["DATE"] = date
                compsegsrecords.append(rec_data)
        elif kword.name == "WELSEGS":
            # First record contains meta-information for well
            # (opm deck returns default values for unspecified items.)
            welsegsdict = parse_opmio_deckrecord(
                kword[0], "WELSEGS", itemlistname="records", recordindex=0
            )
            # Loop over all subsequent records.
            for recidx in range(1, len(kword)):
                rec = kword[recidx]
                # WARNING: We assume that SEGMENT1 === SEGMENT2 (!!!) (if not,
                # we need to loop over a range just as for layer in compdat)
                rec_data = welsegsdict.copy()
                rec_data["DATE"] = date
                rec_data.update(
                    parse_opmio_deckrecord(
                        rec, "WELSEGS", itemlistname="records", recordindex=1
                    )
                )
                if "INFO_TYPE" in rec_data and rec_data["INFO_TYPE"] == "ABS":
                    rec_data["SEGMENT_MD"] = rec_data["SEGMENT_LENGTH"]
                welsegsrecords.append(rec_data)
        elif kword.name == "TSTEP":
            logger.warning("Possible premature stop at first TSTEP")
            break

    compdat_df = pd.DataFrame(compdatrecords)

    if unroll and not compdat_df.empty:
        compdat_df = unrolldf(compdat_df, "K1", "K2")

    compsegs_df = pd.DataFrame(compsegsrecords)

    welsegs_df = pd.DataFrame(welsegsrecords)
    if unroll and not welsegs_df.empty:
        welsegs_df = unrolldf(welsegs_df, "SEGMENT1", "SEGMENT2")

    return dict(COMPDAT=compdat_df, COMPSEGS=compsegs_df, WELSEGS=welsegs_df)


def postprocess():
    """Postprocessing of the compdat data, merging.

    This function is NOT FINISHED"""
    # compdat_df = pd.read_csv("compdat.csv")
    compsegs_df = pd.read_csv("compsegs.csv")
    welsegs_df = pd.read_csv("welsegs.csv")

    #  We need different handling of ICD's and non-ICD wells due
    #  to the complex WELSEGS structure:
    #
    # ICD wells:
    # 1. First compdata is merged with compsegs (non-ICD
    #    should be stripped away).
    # 2. Then that product is merged with welsegs on 'branch'
    # 3. Then that product is merged again with welsegs, where
    #    we join on 'join_segment' and 'segment'
    # 4. Then we finally have the mapping between completed
    #    cells and branch number
    #
    # Non-ICD wells:
    # 1. Merge compdata and compsegs
    # 2. Then we are ready.. compsegs contains the correct branch number

    # compdatsegs = pd.merge(compdat_df, compsegs_df, on=["date", "well", "i", "j", "k"])
    # WARNING: Only correct for dual-branch wells,
    # not triple-branach wells with ICD..
    compsegs_icd_df = compsegs_df[compsegs_df.branch > 2]
    # icd_wells = compsegs_icd_df.well.unique()
    compdatsegwel_icd_df = pd.merge(
        compsegs_icd_df, welsegs_df, on=["date", "well", "branch"]
    )
    del compdatsegwel_icd_df["segment"]  # we don't need this
    compdatsegwel_icd_df.rename(columns={"branch": "icd_branch"}, inplace=True)
    compdatsegwel_icd_df.rename(columns={"join_segment": "segment"}, inplace=True)
    # alldata_icd = pd.merge(
    #     compdatsegwel_icd_df, welsegs_df, on=["date", "well", "segment"]
    # )


def unrolldf(dframe, start_column="K1", end_column="K2"):
    """Unroll dataframes, where some column pairs indicate
    a range where data applies.

    After unrolling, column pairs with ranges are transformed
    into multiple rows, with no ranges.

    Example: COMPDAT supports K1, K2 intervals for multiple cells::

      COMPDAT
        'OP1' 33 44 10 11 /
      /

    is transformed/unrolled so it would be equal to::

      COMPDAT
        'OP1' 33 44 10 10 /
        'OP1' 33 44 11 11 /
      /

    The latter is easier to work with in Pandas dataframes

    Args:
        dframe (pd.DataFrame): Dataframe to be unrolled
        start_column (str): Column name that contains the start of
            a range.
        end_column (str): Column name that contains the corresponding end
            of the range.

    Returns:
        pd.Dataframe, Unrolled version. Identical to input if none of
            rows had any ranges.
    """
    if dframe.empty:
        return dframe
    if start_column not in dframe and end_column not in dframe:
        logger.warning(
            "Cannot unroll on non-existing columns %s and %s", start_column, end_column
        )
        return dframe
    start_eq_end_bools = dframe[start_column] == dframe[end_column]
    unrolled = dframe[start_eq_end_bools]
    list_unrolled = []
    if (~start_eq_end_bools).any():
        for _, rangerow in dframe[~start_eq_end_bools].iterrows():
            for k_idx in range(
                int(rangerow[start_column]), int(rangerow[end_column]) + 1
            ):
                rangerow[start_column] = k_idx
                rangerow[end_column] = k_idx
                list_unrolled.append(rangerow.copy())
    if list_unrolled:
        unrolled = pd.concat([unrolled, pd.DataFrame(list_unrolled)], axis=0)
    return unrolled


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
        default="compdat.csv",
    )
    parser.add_argument(
        "--initvectors",
        help="List of INIT vectors to merge into the data",
        nargs="+",
        default=None,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def main():
    """Entry-point for module, for command line utility
    """
    logger.warning("compdat2csv is deprecated, use 'ecl2csv compdat <args>' instead")
    parser = argparse.ArgumentParser()
    parser = fill_parser(parser)
    args = parser.parse_args()
    compdat2df_main(args)


def compdat2df_main(args):
    """Entry-point for module, for command line utility"""
    if args.verbose:
        logger.setLevel(logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    compdat_df = df(eclfiles, initvectors=args.initvectors)
    if compdat_df.empty:
        logger.warning("Empty COMPDAT data being written to disk!")
    compdat_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)


def df(eclfiles, initvectors=None):
    """Main function for Python API users

    Supports only COMPDAT information for now. Will
    add a zone-name if a zonefile is found alongside

    Returns:
        pd.Dataframe with one row pr cell to well connection
    """
    compdat_df = deck2dfs(eclfiles.get_ecldeck())["COMPDAT"]
    compdat_df = unrolldf(compdat_df)

    if initvectors:
        compdat_df = merge_initvectors(
            eclfiles, compdat_df, initvectors, ijknames=["I", "J", "K1"]
        )

    zonemap = eclfiles.get_zonemap()
    if zonemap:
        logger.info("Merging zonemap into compdat")
        compdat_df = merge_zones(compdat_df, zonemap)

    return compdat_df
