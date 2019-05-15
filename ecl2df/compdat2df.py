#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract COMPDAT, WELSEGS and COMPSEGS from an Eclipse deck

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import argparse
import datetime
import pandas as pd

from .eclfiles import EclFiles


def parse_ecl_month(eclmonth):
    eclmonth2num = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "JLY": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }
    return eclmonth2num[eclmonth]


def unrollcompdatdf(compdat_df):
    """COMPDAT to Eclipse support K1, K2 intervals for multiple cells

    This is unwanted when exported to file, unroll these intervals
    into multiple rows where K1 == K2 (duplicating the rest of the data)
    """
    k1eqk2bools = compdat_df["K1"] == compdat_df["K2"]
    unrolled = compdat_df[k1eqk2bools]
    list_unrolled = []
    if (~k1eqk2bools).any():
        for _, rangerow in compdat_df[~k1eqk2bools].iterrows():
            for k in range(int(rangerow["K1"]), int(rangerow["K2"]) + 1):
                rangerow["K1"] = k
                rangerow["K2"] = k
                list_unrolled.append(rangerow.copy())
    if list_unrolled:
        unrolled = pd.concat([unrolled, pd.DataFrame(list_unrolled)], axis=0)
    return unrolled


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

WELSEGSKEYS = [
    "WELL",  # "Name of the well"
    "DEPTH",  # "Depth of the nodal point of the top segment"
    "LENGTH", # Length down tubing to nodal point of top segment"
    "WELLBORE_VOLUME",  # Effective wellbore volume of the top segment
    "INFO_TYPE",  # Type of tubing length and depth information, INC or ABS
    "PRESSURE_COMPONENTS",  # How to calculate pressure drop in each segment
    "FLOW_MODEL",
    "TOP_X",
    "TOP_Y",  # END OF FIRST RECORD FOR E100. E300 has some more.
    "SEGMENT",  # For each subseqent record
    "BRANCH",
    "JOIN_SEGMENT",
    "SEGMENT_LENGTH",
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

    For Dataframe columnnames, we prefer the RMS terms due to the
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


def deck2compdatsegsdfs(deck):
    """Loop through the deck and pick up information found

    The loop over the deck is a state machine, as it has to pick up dates

    Return:
        tuple with 3 dataframes, compdat, compsegs, welsegs.

    TODO: Support TSTEP
    """
    compdatrecords = []  # List of dicts of every line in input file
    compsegsrecords = []
    welsegsrecords = []
    date = None  # DATE columns will always be there, but can contain NaN
    for kw in deck:
        if kw.name == "DATES" or kw.name == "START":
            for rec in kw:
                day = rec["DAY"][0]
                month = rec["MONTH"][0]
                year = rec["YEAR"][0]
                date = datetime.date(year=year, month=parse_ecl_month(month), day=day)
                print("Parsing at date " + str(date))
        elif kw.name == "COMPDAT":
            for rec in kw:  # Loop over the lines inside COMPDAT record
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
        elif kw.name == "COMPSEGS":
            well = kw[0][0][0]
            for recidx in range(1, len(kw)):
                rec_data = {}
                rec_data["WELL"] = well
                rec_data["DATE"] = date
                rec = kw[recidx]
                for rec_key in COMPSEGSKEYS:
                    try:
                        if rec[rec_key]:
                            rec_data[rec_key] = rec[rec_key][0]
                    except ValueError:
                        pass
                compsegsrecords.append(rec_data)
        elif kw.name == "WELSEGS":
            # First record contains meta-information for well
            # (sunbeam deck returns default values for unspecified items.)
            welsegsdict = {}
            welsegsdict["WELL"] = well = kw[0][0][0]
            welsegsdict["DEPTH"] = kw[0][1][0]
            welsegsdict["LENGTH"] = kw[0][2][0]
            welsegsdict["WBOREVOL"] = kw[0][3][0]
            welsegsdict["INFO"] = kw[0][4][0]
            welsegsdict["PRES_COMP"] = kw[0][5][0]
            welsegsdict["FLOWMODEL"] = kw[0][6][0]
            welsegsdict["TOP_X"] = kw[0][7][0]
            welsegsdict["TOP_Y"] = kw[0][8][0]
            # Loop over all subsequent records.
            for recidx in range(1, len(kw)):
                rec = kw[recidx]
                # WARNING: We assume that SEGMENT1 === SEGMENT2 (!!!) (if not,
                # we need to loop over a range just as for layer in compdat)
                rec_data = welsegsdict.copy()
                rec_data["DATE"] = date
                for rec_key in WELSEGSKEYS:
                    try:
                        if rec[rec_key]:
                            rec_data[rec_key] = rec[rec_key][0]
                    except ValueError:
                        print(rec_key)
                        pass
                welsegsrecords.append(rec_data)
        elif kw.name == "TSTEP":
            print("WARNING: Possible premature stop at first TSTEP")
            break

    compdat_df = pd.DataFrame(compdatrecords)
    compdat_df = unrollcompdatdf(compdat_df)
    compsegs_df = pd.DataFrame(compsegsrecords)
    welsegs_df = pd.DataFrame(welsegsrecords)

    return (compdat_df, compsegs_df, welsegs_df)


def postprocess():
    compdat_df = pd.read_csv("compdat.csv")
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

    compdatsegs = pd.merge(compdat_df, compsegs_df, on=["date", "well", "i", "j", "k"])
    # WARNING: Only correct for dual-branch wells,
    # not triple-branach wells with ICD..
    compsegs_icd_df = compsegs_df[compsegs_df.branch > 2]
    icd_wells = compsegs_icd_df.well.unique()
    compdatsegwel_icd_df = pd.merge(
        compsegs_icd_df, welsegs_df, on=["date", "well", "branch"]
    )
    del compdatsegwel_icd_df["segment"]  # we don't need this
    compdatsegwel_icd_df.rename(columns={"branch": "icd_branch"}, inplace=True)
    compdatsegwel_icd_df.rename(columns={"join_segment": "segment"}, inplace=True)
    alldata_icd = pd.merge(
        compdatsegwel_icd_df, welsegs_df, on=["date", "well", "segment"]
    )


def parse_args():
    """Parse sys.argv using argparse"""
    parser = argparse.ArgumentParser()
    parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file.",
        default="compdat.csv",
    )
    return parser.parse_args()


def main():
    """Entry-point for module, for command line utility"""
    args = parse_args()
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    (compdat_df, compsegs_df, welsegs_df) = deck2compdatsegsdfs(deck)
    compdat_df.to_csv("compdat.csv", index=False)
    compsegs_df.to_csv("compsegs.csv", index=False)
    welsegs_df.to_csv("welsegs.csv", index=False)
    compdat_df = unrollcompdatdf(compdat_df)
    compdat_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)
