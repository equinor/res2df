#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract transmissibility information from Eclipse output files as Dataframes.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import sys
import logging
import argparse
import fnmatch
import datetime
import dateutil.parser

import numpy as np
import pandas as pd

import ecl2df
from ecl.eclfile import EclFile
from .eclfiles import EclFiles

from .common import merge_zones


def df(eclfiles, vectors=None):
    """Make a dataframe of the neighbour transmissibilities.

    The TRANX, TRANY and TRANZ (whenever nonzero) will be used
    to produce a row representing a cell-pair where there is
    transmissibility.

    You will get a dataframe with the columns
        I1, J1, K1, I2, J2, K2, DIR, TRAN
    similar to what you get from non-neighbour connection export.

    The DIR column indicates the direction, and can take the
    string values I, J or K.

    If you ask for additional vectors, like FIPNUM, then
    you will get a corresponding FIPNUM1 and FIPNUM2 added.

    Args:
        eclfiles (EclFiles): An object representing your Eclipse run
        vectors (str or list): Eclipse INIT vectors that you want to include

    Returns:
        pd.DataFrame: with one cell-pair pr. row. Empty dataframe if error.
    """
    if not vectors:
        vectors = []
    if not isinstance(vectors, list):
        vectors = [vectors]
    grid_df = ecl2df.grid.df(eclfiles).set_index(["I", "J", "K"])
    existing_vectors = [vec for vec in vectors if vec in grid_df.columns]
    if len(existing_vectors) < len(vectors):
        logging.warning(
            "Vectors %s not found, skipping", str(set(vectors) - set(existing_vectors))
        )
    vectors = existing_vectors
    transrows = []
    for ijk, row in grid_df.iterrows():
        if abs(row["TRANX"]) > 0:
            transrow = [
                int(ijk[0]),
                int(ijk[1]),
                int(ijk[2]),
                int(ijk[0] + 1),
                int(ijk[1]),
                int(ijk[2]),
                "I",
                row["TRANX"],
            ]
            transrows.append(transrow)
        if abs(row["TRANY"]) > 0:
            transrow = [
                int(ijk[0]),
                int(ijk[1]),
                int(ijk[2]),
                int(ijk[0]),
                int(ijk[1] + 1),
                int(ijk[2]),
                "J",
                row["TRANY"],
            ]
            transrows.append(transrow)
        if abs(row["TRANZ"]) > 0:
            transrow = [
                int(ijk[0]),
                int(ijk[1]),
                int(ijk[2]),
                int(ijk[0]),
                int(ijk[1]),
                int(ijk[2] + 1),
                "K",
                row["TRANZ"],
            ]
            transrows.append(transrow)
    trans_df = pd.DataFrame(data=transrows)
    columnnames = ["I1", "J1", "K1", "I2", "J2", "K2", "DIR", "TRAN"]
    trans_df.columns = columnnames
    # If we have additional vectors we want, merge them in:
    if vectors:
        grid_df = grid_df.reset_index()
        trans_df = pd.merge(
            trans_df,
            grid_df[["I", "J", "K"] + vectors],
            left_on=["I1", "J1", "K1"],
            right_on=["I", "J", "K"],
        )
        del trans_df["I"]
        del trans_df["J"]
        del trans_df["K"]
        trans_df = pd.merge(
            trans_df,
            grid_df[["I", "J", "K"] + vectors],
            left_on=["I2", "J2", "K2"],
            right_on=["I", "J", "K"],
            suffixes=("1", "2"),
        )
        del trans_df["I"]
        del trans_df["J"]
        del trans_df["K"]
    for vec in vectors:
        columnnames.append(vec + "1")
        columnnames.append(vec + "2")
    return trans_df


def fill_parser(parser):
    """Set up sys.argv parser.

    Arguments:
        parser: argparse.ArgumentParser or argparse.subparser
    """
    parser.add_argument(
        "DATAFILE",
        help="Name of Eclipse DATA file. " + "INIT and EGRID file must lie alongside.",
    )
    parser.add_argument("--vectors", nargs="+", help="Extra INIT vectors to be added")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file.",
        default="eclgrid.csv",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def trans2df_main(args):
    """This is the command line API"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    trans_df = df(eclfiles, vectors=args.vectors,)
    if args.output == "-":
        # Ignore pipe errors when writing to stdout.
        from signal import signal, SIGPIPE, SIG_DFL

        signal(SIGPIPE, SIG_DFL)
        trans_df.to_csv(sys.stdout, index=False)
    else:
        trans_df.to_csv(args.output, index=False)
        print("Wrote to " + args.output)
