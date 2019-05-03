#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract COMPDAT, WELSEGS and COMPSEGS from an Eclipse deck

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

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
    return compdat_df


def sunbeam2rmsterm(reckey):
    """Sunbeam authors and Roxar RMS authors have interpreted the Eclipse documentation
    ever so slightly different when naming the data.

    For Dataframe columnnames, we prefer the RMS terms due to the one very long one, and mixed-case in sunbeam"""
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
    return thedict[reckey]


compsegs_df = pd.DataFrame(
    columns=["date", "well", "i", "j", "k", "branch", "distance_start", "distance_end"]
)
# , 'direction','end_ijk', 'center_depth', 'thermal_length', 'segment_number'])

welsegs_df = pd.DataFrame(
    columns=[
        "date",
        "well",
        "depth",
        "length",
        "wellbore_volume",
        "info_type",
        "pressure_components",
        "flow_model",
        "top_x",
        "top_y",
        "segment",
        "branch",
        "join_segment",
        "segment_length",
        "depth_change",
        "diameter",
        "roughness",
    ]
)
# , 'area', 'volume', 'length_x', 'length_y'])


# print "Date,Well,i,j,k,state,sat_table,connectiontrans,diameter,kh,skin,d_factor,dir,pr"
def deck2compdatsegsdfs(eclfiles):
    """Loop through the deck and pick up information found

    The loop over the deck is a state machine, as it has to pick up dates
    This will not work for TSTEP!!
    """
    deck = eclfiles.get_ecldeck()
    compdat_df = pd.DataFrame(
        columns=[
            "date",
            "well",
            "i",
            "j",
            "k",
            "state",
            "sat_table",
            "connectiontrans",
            "diam",
            "kh",
            "skin",
            "d_factor",
            "direction",
            "pr",
        ]
    )
    compsegs_df = pd.DataFrame(
        columns=[
            "date",
            "well",
            "i",
            "j",
            "k",
            "branch",
            "distance_start",
            "distance_end",
        ]
    )
    # , 'direction','end_ijk', 'center_depth', 'thermal_length', 'segment_number'])

    welsegs_df = pd.DataFrame(
        columns=[
            "date",
            "well",
            "depth",
            "length",
            "wellbore_volume",
            "info_type",
            "pressure_components",
            "flow_model",
            "top_x",
            "top_y",
            "segment",
            "branch",
            "join_segment",
            "segment_length",
            "depth_change",
            "diameter",
            "roughness",
        ]
    )
    # , 'area', 'volume', 'length_x', 'length_y'])

    for kw in deck:
        if kw.name == "DATES":
            for rec in kw:
                day = rec["DAY"][0]
                month = rec["MONTH"][0]
                year = rec["YEAR"][0]
                # Make datetime.date instead:
                datestr = str(year) + "-" + str(parse_ecl_month(month)) + "-" + str(day)
        elif kw.name == "COMPDAT":
            for rec in kw:
                for layer in range(int(rec["K1"][0]), int(rec["K2"][0]) + 1):
                    compdat_df.loc[len(compdat_df)] = [
                        datestr,
                        rec["WELL"][0],
                        rec["I"][0],
                        rec["J"][0],
                        str(layer),
                        rec["STATE"][0],
                        rec["SAT_TABLE"][0],
                        rec["CONNECTION_TRANSMISSIBILITY_FACTOR"][0],
                        rec["DIAMETER"][0],
                        rec["Kh"][0],
                        rec["SKIN"][0],
                        0,  # D_FACTOR is defaulted..
                        # rec['D_FACTOR'][0],
                        rec["DIR"][0],
                        rec["PR"][0],
                    ]
        elif kw.name == "COMPSEGS":
            well = kw[0][0][0]
            for recidx in range(1, len(kw)):
                rec = kw[recidx]
                compsegs_df.loc[len(compsegs_df)] = [
                    datestr,
                    well,
                    str(int(rec["I"][0])),
                    str(int(rec["J"][0])),
                    str(int(rec["K"][0])),
                    str(int(rec["BRANCH"][0])),
                    rec["DISTANCE_START"][0],
                    rec["DISTANCE_END"][0],
                ]  # q, rec['DIRECTION'][0], rec['END_IJK'][0], rec['CENTER_DEPTH'][0], rec['THERMAL_LENGTH'][0], rec['SEGMENT_NUMBER'][0]]
        elif kw.name == "WELSEGS":
            well = kw[0][0][0]
            depth = kw[0][1][0]
            length = kw[0][2][0]
            wellbore_volume = kw[0][3][0]
            info_type = kw[0][4][0]
            pressure_components = kw[0][5][0]
            flow_model = kw[0][6][0]
            top_x = kw[0][7][0]
            top_y = kw[0][8][0]
            for recidx in range(1, len(kw)):
                rec = kw[recidx]
                # WARNING: We assume that SEGMENT1 === SEGMENT2 (!!!) (if not, we need to loop over a range just as for layer in compdat)
                welsegs_df.loc[len(welsegs_df)] = [
                    datestr,
                    well,
                    depth,
                    length,
                    wellbore_volume,
                    info_type,
                    pressure_components,
                    flow_model,
                    top_x,
                    top_y,
                    rec["SEGMENT1"][0],
                    rec["BRANCH"][0],
                    rec["JOIN_SEGMENT"][0],
                    rec["SEGMENT_LENGTH"][0],
                    rec["DEPTH_CHANGE"][0],
                    rec["DIAMETER"][0],
                    rec["ROUGHNESS"][0],
                ]

    striptables = True
    if striptables:
        compdat_df.drop(
            ["state", "sat_table", "diam", "skin", "d_factor", "direction", "pr"],
            inplace=True,
            axis=1,
        )
        welsegs_df.drop(
            [
                "wellbore_volume",
                "info_type",
                "pressure_components",
                "flow_model",
                "top_x",
                "top_y",
                "diameter",
                "roughness",
            ],
            inplace=True,
            axis=1,
        )

    return compdat_df


def postprocess():
    compdat_df = pd.read_csv("compdat.csv")
    compsegs_df = pd.read_csv("compsegs.csv")
    welsegs_df = pd.read_csv("welsegs.csv")

    #    We need different handling of ICD's and non-ICD wells due to the complex WELSEGS structure:
    #
    # ICD wells:
    # 1. First compdata is merged with compsegs (non-ICD should be stripped away).
    # 2. Then that product is merged with welsegs on 'branch'
    # 3. Then that product is merged again with welsegs, where we join on 'join_segment' and 'segment'
    # 4. Then we finally have the mapping between completed cells and branch number
    #
    # Non-ICD wells:
    # 1. Merge compdata and compsegs
    # 2. Then we are ready.. compsegs contains the correct branch number

    compdatsegs = pd.merge(compdat_df, compsegs_df, on=["date", "well", "i", "j", "k"])
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
