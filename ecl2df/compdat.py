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
from .common import parse_ecl_month, merge_zones
from .grid import merge_initvectors


# Sunbeam terms:
COMPDATKEYS = [
    "WELL",
    "I",
    "J",
    "K1",
    "K2",
    "STATE",
    "SAT_TABLE",
    "CONNECTION_TRANSMISSIBILITY_FACTOR",
    "DIAMETER",
    "Kh",
    "SKIN",
    "D_FACTOR",
    "DIR",
    "PR",
]

COMPSEGSKEYS = [
    "I",
    "J",
    "K",
    "BRANCH",
    "DISTANCE_START",
    "DISTANCE_END",
    "DIRECTION",
    "END_IJK",
    "CENTER_DEPTH",
    "THERMAL_LENGTH",
    "SEGMENT_NUMBER",
]

# Based on https://github.com/OPM/opm-common/blob/master/
#        src/opm/parser/eclipse/share/keywords/000_Eclipse100/W/WELSEGS
WELSEGSKEYS = [
    "WELL",  # "Name of the well"
    "DEPTH",  # "Depth of the nodal point of the top segment"
    "LENGTH",  # Length down tubing to nodal point of top segment"
    "WELLBORE_VOLUME",  # Effective wellbore volume of the top segment
    "INFO_TYPE",  # Type of tubing length and depth information, INC or ABS
    "PRESSURE_COMPONENTS",  # How to calculate pressure drop in each segment
    "FLOW_MODEL",
    "TOP_X",
    "TOP_Y",  # END OF FIRST RECORD FOR E100. E300 has some more.
    "SEGMENT1",  # For each subseqent record
    "SEGMENT2",
    "BRANCH",
    "JOIN_SEGMENT",
    "SEGMENT_LENGTH",  # Copied to SEGMENT_MD, as it can be both, depending on INFO_TYPE
    "DEPTH_CHANGE",
    "DIAMETER",
    "ROUGHNESS",
    "AREA",
    "VOLUME",
    "LENGTH_X",
    "LENGTH_Y",
]


def sunbeam2rmsterm(reckey):
    """Sunbeam authors and Roxar RMS authors have interpreted the Eclipse
    documentation ever so slightly different when naming the data.

    For COMPDAT dataframe columnnames, we prefer the RMS terms due to the
    one very long one, and mixed-case in sunbeam

    Returns:
        str with translated term, or of no translation available
        the term is returned unchanged.
    """

    thedict = {
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
    return thedict.get(reckey, reckey)


def deck2compdatsegsdfs(deck, start_date=None):
    """Deprecated function name"""
    logging.warning("Deprecated method name: deck2compdatsegsdfs(), use deck2dfs()")
    return deck2dfs(deck, start_date)


def deck2dfs(deck, start_date=None, unroll=True):
    """Loop through the deck and pick up information found

    The loop over the deck is a state machine, as it has to pick up dates

    Args:
        deck (sunbeam.libsunbeam.Deck): A deck representing the schedule
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
                day = rec["DAY"][0]
                month = rec["MONTH"][0]
                year = rec["YEAR"][0]
                date = datetime.date(year=year, month=parse_ecl_month(month), day=day)
                logging.info("Parsing at date %s", str(date))
        elif kword.name == "TSTEP":
            if not date:
                logging.critical("Can't use TSTEP when there is no start_date")
                return {}
            for rec in kword:
                steplist = rec[0]
                # Assuming not LAB units, then the unit is days.
                days = sum(steplist)
                date += datetime.timedelta(days=days)
                logging.info(
                    "Advancing %s days to %s through TSTEP", str(days), str(date)
                )
        elif kword.name == "COMPDAT":
            for rec in kword:  # Loop over the lines inside COMPDAT record
                rec_data = {}
                rec_data["DATE"] = date
                for rec_key in COMPDATKEYS:
                    try:
                        if rec[rec_key]:
                            rec_data[sunbeam2rmsterm(rec_key)] = rec[rec_key][0]
                        # "rec_key in rec" does not work..
                    except ValueError:
                        pass
                compdatrecords.append(rec_data)
        elif kword.name == "COMPSEGS":
            well = kword[0][0][0]
            for recidx in range(1, len(kword)):
                rec_data = {}
                rec_data["WELL"] = well
                rec_data["DATE"] = date
                rec = kword[recidx]
                for rec_key in COMPSEGSKEYS:
                    try:
                        if rec[rec_key]:
                            rec_data[rec_key] = rec[rec_key][0]
                    except ValueError:
                        pass
                compsegsrecords.append(rec_data)
        elif kword.name == "WELSEGS":
            # First record contains meta-information for well
            # (sunbeam deck returns default values for unspecified items.)
            welsegsdict = {}
            welsegsdict["WELL"] = well = kword[0][0][0]
            welsegsdict["DEPTH"] = kword[0][1][0]
            welsegsdict["LENGTH"] = kword[0][2][0]
            welsegsdict["WELLBORE_VOLUME"] = kword[0][3][0]
            welsegsdict["INFO_TYPE"] = kword[0][4][0]
            welsegsdict["PRESSURE_COMPONENTS"] = kword[0][5][0]
            welsegsdict["FLOW_MODEL"] = kword[0][6][0]
            welsegsdict["TOP_X"] = kword[0][7][0]
            welsegsdict["TOP_Y"] = kword[0][8][0]
            # Loop over all subsequent records.
            for recidx in range(1, len(kword)):
                rec = kword[recidx]
                # WARNING: We assume that SEGMENT1 === SEGMENT2 (!!!) (if not,
                # we need to loop over a range just as for layer in compdat)
                rec_data = welsegsdict.copy()
                rec_data["DATE"] = date
                for rec_key in WELSEGSKEYS:
                    try:
                        if rec[rec_key]:
                            rec_data[rec_key] = rec[rec_key][0]
                    except ValueError:
                        pass
                if "INFO_TYPE" in rec_data and rec_data["INFO_TYPE"] == "ABS":
                    rec_data["SEGMENT_MD"] = rec_data["SEGMENT_LENGTH"]
                welsegsrecords.append(rec_data)
        elif kword.name == "TSTEP":
            logging.warning("Possible premature stop at first TSTEP")
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
        logging.warning(
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
    logging.warning("compdat2csv is deprecated, use 'ecl2csv compdat <args>' instead")
    parser = argparse.ArgumentParser()
    parser = fill_parser(parser)
    args = parser.parse_args()
    compdat2df_main(args)


def compdat2df_main(args):
    """Entry-point for module, for command line utility"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    compdat_df = df(eclfiles, initvectors=args.initvectors)
    if compdat_df.empty:
        logging.warning("Empty COMPDAT data being written to disk!")
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
        logging.info("Merging zonemap into compdat")
        compdat_df = merge_zones(compdat_df, zonemap)

    return compdat_df
