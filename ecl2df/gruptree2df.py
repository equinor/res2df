#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract GRUPTREE information from an Eclipse deck

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys
import datetime
import dateutil
import argparse
import pandas as pd

from .eclfiles import EclFiles
from .common import parse_ecl_month

def gruptree2df(deck, startdate=None, welspecs=True):
    """Extract all group information from a deck
    and present as a Pandas Dataframe of all edges.

    The gruptree is a time dependent property,
    with accumulative effects from new occurences of
    GRUPTREE or WELSPECS.

    Whenever the tree changes, the previous tree is copied
    and a new complete tree is added to the dataframe tagged
    with the new date.

    startdate is only relevant when START is not in the deck.
    """

    date = None
    dflist = []  # list of list of rows.
    currentedges = dict()  # Indexed by tuple of two strings. Value is type.
    found_gruptree = False  # Flags which will tell when a new GRUPTREE or
    found_welspecs = False  # WELSPECS have been encountered.
    for kw in deck:
        if kw.name == "DATES" or kw.name == "START":
            if len(currentedges) and (found_gruptree or found_welspecs):
                # Store all edges in dataframe at the previous date.
                for edgename, value in currentedges.iteritems():
                    dflist.append([date, edgename[0], edgename[1], value])
                found_gruptree = False
                found_welspecs = False
            for rec in kw:
                day = rec["DAY"][0]
                month = rec["MONTH"][0]
                year = rec["YEAR"][0]
                date = datetime.date(year=year, month=parse_ecl_month(month), day=day)
        if kw.name == "GRUPTREE":
            found_gruptree = True
            for edgerec in kw:
                child = edgerec[0][0]
                parent = edgerec[1][0]
                currentedges[(child, parent)] = "GRUPTREE"
        if kw.name == "WELSPECS" and welspecs:
            found_welspecs = True
            for wellrec in kw:
                wellname = wellrec[0][0]
                group = wellrec[1][0]
                currentedges[(wellname, group)] = "WELSPECS"

    df = pd.DataFrame(columns=["DATE", "CHILD", "PARENT", "TYPE"], data=dflist)
    df["DATE"] = pd.to_datetime(df["DATE"])
    return df


def gruptree2dict(deck, date="END", welspecs=True):
    """Extract the GRUPTREE information as a tree structure
    in a dict.

    Example result:
    {'FIELD': ['WI', 'OP'],
     'OP': ['OP_2', 'OP_3', 'OP_4', 'OP_5', 'OP_1'],
     'WI': ['WI_1', 'WI_2', 'WI_3']}

    Returns an empty dict if there is no GRUPTREE in the deck."""

    df = gruptree2df(deck, welspecs).set_index("DATE")
    if isinstance(date, str):
        if date == "START":
            date = df.index[0]
        if date == "END":
            date = df.index[-1]
        else:
            try:
                isodate = dateutil.parser.isoparse(dates).date()
            except ValueError:
                raise ValueError("date " + str(dates) + " not understood")

    if date not in df.index:
        return {}
    else:
        return gruptreedf2dict(df.loc[date])


def gruptreedf2dict(df):
    tree = {}
    for _, edge in df.iterrows():
        tree.setdefault(edge["PARENT"], []).append(edge["CHILD"])
    return tree


def parse_args():
    """Parse sys.argv using argparse"""
    parser = argparse.ArgumentParser()
    parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file.",
        default="gruptree.csv",
    )
    return parser.parse_args()


def main():
    """Entry-point for module, for command line utility"""
    args = parse_args()
    eclfiles = EclFiles(args.DATAFILE)
    gruptree_df = gruptree2df(eclfiles.get_ecldeck())
    if args.output == "-":
        # Ignore pipe errors when writing to stdout.
        from signal import signal, SIGPIPE, SIG_DFL

        signal(SIGPIPE, SIG_DFL)
        gruptree_df.to_csv(sys.stdout, index=False)
    else:
        gruptree_df.to_csv(args.output, index=False)
        print("Wrote to " + args.output)
