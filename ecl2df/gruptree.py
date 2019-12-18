#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract GRUPTREE information from an Eclipse deck

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys
import logging
import datetime
import argparse
import collections
import dateutil
import pandas as pd

from .eclfiles import EclFiles
from .common import parse_ecl_month

# From: https://github.com/OPM/opm-common/blob/master/
#       src/opm/parser/eclipse/share/keywords/000_Eclipse100/G/GRUPNET
GRUPNETKEYS = [
    "NAME",
    "TERMINAL_PRESSURE",
    "VFP_TABLE",
    "ALQ",
    "SUB_SEA_MANIFOLD",
    "LIFT_GAS_FLOW_THROUGH",
    "ALQ_SURFACE_EQV",
]


def gruptree2df(deck, startdate=None, welspecs=True):
    """Deprecated function name"""
    logging.warning("Deprecated function name, gruptree2df")
    return deck2df(deck, startdate, welspecs)


def deck2df(deck, startdate=None, welspecs=True):
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

    gruptreerecords = []  # list of dict of rows containing an edge.
    grupnetrecords = []

    # In order for the GRUPTREE keywords to accumulate, we
    # store the edges as a dictionary indexed by the edge
    # (which is a tuple of child and parent).
    # The value of the dictionary is GRUPTREE or WELSPECS
    currentedges = dict()

    grupnet_df = pd.DataFrame()

    found_gruptree = False  # Flags which will tell when a new GRUPTREE or
    found_welspecs = False  # WELSPECS have been encountered.
    found_grupnet = False  # GRUPNET has been encountered
    for kword in deck:
        if kword.name == "DATES" or kword.name == "START" or kword.name == "TSTEP":
            # Whenever we encounter a new DATES, it means that
            # we have processed all the GRUPTREE and WELSPECS that
            # have occured since the last date, so this is the chance
            # to dump the parsed data. Also we dump the *entire* tree
            # at every date with a change, not only the newfound edges.
            if currentedges and (found_gruptree or found_welspecs or found_grupnet):
                if date is None:
                    logging.warning(
                        "WARNING: No date parsed, maybe you should pass --startdate"
                    )
                    logging.warning("         Using 1900-01-01")
                    date = datetime.date(year=1900, month=1, day=1)
                # Store all edges in dataframe at the previous date.
                for edgename, value in currentedges.items():
                    rec_dict = {
                        "DATE": date,
                        "CHILD": edgename[0],
                        "PARENT": edgename[1],
                        "TYPE": value,
                    }
                    if edgename[0] in grupnet_df.index:
                        rec_dict.update(grupnet_df.loc[edgename[0]])
                    gruptreerecords.append(rec_dict)
                found_gruptree = False
                found_welspecs = False
                found_grupnet = False
            # Done dumping the data for the previous date, parse the fresh
            # date:
            if kword.name == "DATES" or kword.name == "START":
                for rec in kword:
                    day = rec["DAY"][0]
                    month = rec["MONTH"][0]
                    year = rec["YEAR"][0]
                    date = datetime.date(
                        year=year, month=parse_ecl_month(month), day=day
                    )
            elif kword.name == "TSTEP":
                for rec in kword:
                    steplist = rec[0]
                    # Assuming not LAB units, then the unit is days.
                    days = sum(steplist)
                    if days <= 0:
                        logging.critical("Invalid TSTEP, summed to %s days", str(days))
                        return pd.DataFrame()
                    date += datetime.timedelta(days=days)
                    logging.info(
                        "Advancing %s days to %s through TSTEP", str(days), str(date)
                    )
            else:
                logging.critical("BUG: Should not get here")
                return pd.DataFrame()
        if kword.name == "GRUPTREE":
            found_gruptree = True
            for edgerec in kword:
                child = edgerec[0][0]
                parent = edgerec[1][0]
                currentedges[(child, parent)] = "GRUPTREE"
        if kword.name == "WELSPECS" and welspecs:
            found_welspecs = True
            for wellrec in kword:
                wellname = wellrec[0][0]
                group = wellrec[1][0]
                currentedges[(wellname, group)] = "WELSPECS"
        if kword.name == "GRUPNET":
            found_grupnet = True
            for rec in kword:
                grupnet_data = {}
                for rec_key in GRUPNETKEYS:
                    try:
                        if rec[rec_key]:
                            grupnet_data[rec_key] = rec[rec_key][0]
                    except ValueError:
                        pass
                grupnetrecords.append(grupnet_data)
            grupnet_df = (
                pd.DataFrame(grupnetrecords)
                .drop_duplicates(subset="NAME", keep="last")
                .set_index("NAME")
            )

    # Ensure we also store any tree information found after the last DATE statement
    if found_gruptree or found_welspecs:
        for edgename, value in currentedges.items():
            rec_dict = {
                "DATE": date,
                "CHILD": edgename[0],
                "PARENT": edgename[1],
                "TYPE": value,
            }
            if edgename[0] in grupnet_df.index:
                rec_dict.update(grupnet_df.loc[edgename[0]])
            gruptreerecords.append(rec_dict)

    dframe = pd.DataFrame(gruptreerecords)
    if "DATE" in dframe:
        dframe["DATE"] = pd.to_datetime(dframe["DATE"])
    return dframe


def gruptree2dict(deck, date="END", welspecs=True):
    """Extract the GRUPTREE information as a tree structure
    in a dict.

    Example result::

      {
        'FIELD': ['WI', 'OP'],
        'OP': ['OP_2', 'OP_3', 'OP_4', 'OP_5', 'OP_1'],
        'WI': ['WI_1', 'WI_2', 'WI_3']
      }

    Returns an empty dict if there is no GRUPTREE in the deck.

    This function might get deprecated in favour of the nested dictionary
    version.
    """

    dframe = gruptree2df(deck, welspecs).set_index("DATE")
    if isinstance(date, str):
        if date == "START":
            date = dframe.index[0]
        if date == "END":
            date = dframe.index[-1]
        else:
            try:
                dateutil.parser.isoparse(date).date()
            except ValueError:
                raise ValueError("date " + str(date) + " not understood")

    if date not in dframe.index:
        return {}
    return gruptreedf2dict(dframe.loc[date])


def gruptreedf2dict(dframe):
    """Convert list of edges into a
    nested dictionary (tree),

    Example::

      {
        'FIELD': {'OP': {'OP_1': {},
        'OP_2': {},
        'OP_3': {},
        'OP_4': {},
        'OP_5': {}},
        'WI': {'WI_1': {}, 'WI_2': {}, 'WI_3': {}}}
      }

    Leaf nodes have empty dictionaries.

    Returns a list of nested dictionary, as we sometimes
    have more than one root
    """
    if dframe.empty:
        return {}
    subtrees = collections.defaultdict(dict)
    edges = []  # List of tuples
    for _, row in dframe.iterrows():
        edges.append((row["CHILD"], row["PARENT"]))
    for child, parent in edges:
        subtrees[parent][child] = subtrees[child]

    children, parents = zip(*edges)
    roots = set(parents).difference(children)
    trees = []
    for root in list(roots):
        trees.append({root: subtrees[root] for root in roots})
    return trees


def dict2treelib(name, nested_dict):
    """Convert a nested dictonary to a treelib Tree
    object. This function is recursive

    Args:
        name: name of root node
        nested_dict: nested dictonary of the children at the root.

    Return:
        treelib.Tree
    """
    import treelib
    tree = treelib.Tree()
    tree.create_node(name, name)
    for child in nested_dict.keys():
        tree.paste(name, dict2treelib(child, nested_dict[child]))
    return tree


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
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def main():
    """Entry-point for module, for command line utility
    """
    logging.warning("gruptree2csv is deprecated, use 'ecl2csv compdat <args>' instead")
    parser = argparse.ArgumentParser()
    parser = fill_parser(parser)
    args = parser.parse_args()
    gruptree2df_main(args)


def gruptree2df_main(args):
    """Entry-point for module, for command line utility"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    if not args.output and not args.prettyprint:
        print("Nothing to do. Set --output or --prettyprint")
        sys.exit(0)
    eclfiles = EclFiles(args.DATAFILE)
    dframe = deck2df(eclfiles.get_ecldeck(), startdate=args.startdate)
    if args.prettyprint:
        for date in dframe["DATE"].dropna().unique():
            print("Date: " + str(date.astype("M8[D]")))
            trees = gruptreedf2dict(dframe[dframe["DATE"] == date])
            for tree in trees:
                rootname = tree.keys()[0]
                print(dict2treelib(rootname, tree[rootname]))
            print("")
    if dframe.empty:
        logging.warning("Empty GRUPTREE dataframe being written to disk!")
    if args.output == "-":
        # Ignore pipe errors when writing to stdout.
        from signal import signal, SIGPIPE, SIG_DFL

        signal(SIGPIPE, SIG_DFL)
        dframe.to_csv(sys.stdout, index=False)
    elif args.output:
        dframe.to_csv(args.output, index=False)
        print("Wrote to " + args.output)


def df(eclfiles, startdate=None):
    """Main function for Python API users"""
    return deck2df(eclfiles.get_ecldeck(), startdate=startdate)
