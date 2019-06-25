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
import treelib
import collections

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

    if startdate is not None:
        date = startdate
    else:
        date = None
    dflist = []  # list of list of rows.
    currentedges = dict()  # Indexed by tuple of two strings. Value is type.
    found_gruptree = False  # Flags which will tell when a new GRUPTREE or
    found_welspecs = False  # WELSPECS have been encountered.
    for kw in deck:
        if kw.name == "DATES" or kw.name == "START":
            if len(currentedges) and (found_gruptree or found_welspecs):
                if date is None:
                    print("WARNING: No date parsed, maybe you should pass --startdate")
                    print("         Using 1900-01-01")
                    date = datetime.date(year=1900, month=1, day=1)
                # Store all edges in dataframe at the previous date.
                for edgename, value in currentedges.items():
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

    # Ensure we also store any tree information found after the last DATE statement
    if found_gruptree or found_welspecs:
        for edgename, value in currentedges.items():
            dflist.append([date, edgename[0], edgename[1], value])

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

    Returns an empty dict if there is no GRUPTREE in the deck.

    This function might get deprecated in favour of the nested dictionary
    version.
    """

    df = gruptree2df(deck, welspecs).set_index("DATE")
    if isinstance(date, str):
        if date == "START":
            date = df.index[0]
        if date == "END":
            date = df.index[-1]
        else:
            try:
                dateutil.parser.isoparse(dates).date()
            except ValueError:
                raise ValueError("date " + str(dates) + " not understood")

    if date not in df.index:
        return {}
    else:
        return gruptreedf2dict(df.loc[date])


def gruptreedf2dict(df):
    """Convert list of edges into a
    nested dictionary (tree), example:

    {'FIELD': {'OP': {'OP_1': {},
     'OP_2': {},
     'OP_3': {},
     'OP_4': {},
     'OP_5': {}},
     'WI': {'WI_1': {}, 'WI_2': {}, 'WI_3': {}}}}

    Leaf nodes have empty dictionaries.

    Returns a list of nested dictionary, as we sometimes
    have more than one root
    """
    if df.empty:
        return {}
    subtrees = collections.defaultdict(dict)
    edges = []  # List of tuples
    for _, row in df.iterrows():
        edges.append((row["CHILD"], row["PARENT"]))
    for child, parent in edges:
        subtrees[parent][child] = subtrees[child]

    children, parents = zip(*edges)
    roots = set(parents).difference(children)
    trees = []
    for root in list(roots):
        trees.append({root: subtrees[root] for root in roots})
    return trees


def dict2treelib(name, d):
    """Convert a nested dictonary to a treelib Tree
    object. This function is recursive

    Args:
        name: name of root node
        d: nested dictonary of the children at the root.
    Return:
        treelib.Tree
    """
    tree = treelib.Tree()
    tree.create_node(name, name)
    for child in d.keys():
        tree.paste(name, dict2treelib(child, d[child]))
    return tree


def parse_args():
    """Parse sys.argv using argparse"""
    parser = argparse.ArgumentParser()
    parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file. No CSV dump if empty",
        default="",
    )
    parser.add_argument(
        "-p",
        "--prettyprint",
        #      type=bool,
        action="store_true",
        help="Pretty-print the tree structure",
    )
    parser.add_argument(
        "--startdate",
        type=str,
        help="First schedule date if not defined in input file, YYYY-MM-DD",
        default=None,
    )
    return parser.parse_args()


def main():
    """Entry-point for module, for command line utility"""
    args = parse_args()
    eclfiles = EclFiles(args.DATAFILE)
    df = gruptree2df(eclfiles.get_ecldeck(), startdate=args.startdate)
    if args.prettyprint:
        for date in df["DATE"].dropna().unique():
            print("Date: " + str(date.astype("M8[D]")))
            trees = gruptreedf2dict(df[df["DATE"] == date])
            for tree in trees:
                rootname = tree.keys()[0]
                print(dict2treelib(rootname, tree[rootname]))
            print("")
    if args.output == "-":
        # Ignore pipe errors when writing to stdout.
        from signal import signal, SIGPIPE, SIG_DFL

        signal(SIGPIPE, SIG_DFL)
        df.to_csv(sys.stdout, index=False)
    elif args.output:
        df.to_csv(args.output, index=False)
        print("Wrote to " + args.output)
