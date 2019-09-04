# -*- coding: utf-8 -*-
"""
Extract NNC information from Eclipse output files.

NNC = Non Neighbour Connection

Inspired by
https://github.com/equinor/libecl/blob/master/python/docs/examples/cmp_nnc.py
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
import argparse
import pandas as pd

from .eclfiles import EclFiles


def nnc2df(eclfiles, pillars=False):
    """Produce a Pandas Dataframe with NNC information

    A NNC is a pair of cells that are not next to each other
    in the index space (I, J, K), and are associated to a
    non-zero transmissibility.

    Columns: I1, J1, K1 (first cell in cell pair)
    I2, J2, K2 (second cell in cell pair), TRAN (transmissibility
    between the two cells)

    Args:
        eclfiles (EclFiles): object that can serve EclFile and EclGrid
            on demand
        pillars (boolean): Set to True if you want to filter to vertical
            (along pillars) connections only.

    Returns:
        pd.DataFrame. Empty if no NNC information found.
    """
    egrid_file = eclfiles.get_egridfile()
    egrid_grid = eclfiles.get_egrid()
    init_file = eclfiles.get_initfile()

    if not ("NNC1" in egrid_file and "NNC2" in egrid_file):
        logging.warning("No NNC data in EGRID")
        return pd.DataFrame()

    # Grid indices for first cell in cell pairs, into a vertical
    # vector. The indices are "global" in libecl terms, and are
    # 1-based (FORTRAN). Convert to zero-based before sending to get_ijk()
    nnc1 = egrid_file["NNC1"][0].numpy_view().reshape(-1, 1)
    logging.info(
        "NNC1: len: %d, min: %d, max: %d (global indices)",
        len(nnc1),
        min(nnc1),
        max(nnc1),
    )
    idx_cols1 = ["I1", "J1", "K1"]
    nnc1_df = pd.DataFrame(
        columns=idx_cols1, data=[egrid_grid.get_ijk(global_index=x - 1) for x in nnc1]
    )
    # Returned indices from get_ijk are zero-based, convert to 1-based indices
    nnc1_df[idx_cols1] = nnc1_df[idx_cols1] + 1

    # Grid indices for second cell in cell pairs
    nnc2 = egrid_file["NNC2"][0].numpy_view().reshape(-1, 1)
    logging.info(
        "NNC2: len: %d, min: %d, max: %d (global indices)",
        len(nnc2),
        min(nnc2),
        max(nnc2),
    )
    idx_cols2 = ["I2", "J2", "K2"]
    nnc2_df = pd.DataFrame(
        columns=idx_cols2, data=[egrid_grid.get_ijk(global_index=x - 1) for x in nnc2]
    )
    nnc2_df[idx_cols2] = nnc2_df[idx_cols2] + 1

    # Obtain transmissibility values, corresponding to the cell pairs above.
    tran = init_file["TRANNNC"][0].numpy_view().reshape(-1, 1)
    logging.info(
        "TRANNNC: len: %d, min: %f, max: %f, mean=%f",
        len(tran),
        min(tran),
        max(tran),
        tran.mean(),
    )
    tran_df = pd.DataFrame(columns=["TRAN"], data=tran)

    nncdf = pd.concat([nnc1_df, nnc2_df, tran_df], axis=1)
    if pillars:
        return filter_vertical(nncdf)
    return nncdf


def filter_vertical(nncdf):
    """Filter to vertical connections

    Arguments:
        nncdf (DataFrame): A dataframe with the columns
            I1, J1, K1, I2, J2, K2.

    Returns:
        Filtered copy of incoming dataframe.
    """
    prelen = len(nncdf)
    vnncdf = nncdf[nncdf["I1"] == nncdf["I2"]]
    vnncdf = vnncdf[vnncdf["J1"] == vnncdf["J2"]]
    postlen = len(vnncdf)
    logging.info(
        "Filtered to vertical connections, %d removed, %d connections kept",
        prelen - postlen,
        postlen,
    )
    return vnncdf


# Remaining functions are for the command line interface


def fill_parser(parser):
    """Set up sys.argv parser

    Arguments:
        parser: argparse.ArgumentParser or argparse.subparser
    """
    parser.add_argument(
        "DATAFILE",
        help="Name of Eclipse DATA file. " + "INIT and EGRID file must lie alongside.",
    )
    parser.add_argument(
        "-p",
        "--pillars",
        "--vertical",
        action="store_true",
        help="Only dump vertical (along pillars) connections",
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Name of output csv file.", default="nnc.csv"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    # args.add_argument("--augment", action='store_true',
    #    (TODO)       help="Add extra data for the cells in the cell pair")
    return parser


def main():
    """Entry-point for module, for command line utility

    It may become deprecated to have a main() function
    and command line utility for each module in ecl2df
    """
    logging.warning("nnc2csv is deprecated, use 'ecl2csv nnc <args>' instead")
    parser = argparse.ArgumentParser()
    fill_parser(parser)
    args = parser.parse_args()
    nnc2df_main(args)


def nnc2df_main(args):
    """Command line access point from main() or from ecl2csv via subparser"""
    if args.verbose:
        logging.basicConfig()
        logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().name = "nnc2df"
    eclfiles = EclFiles(args.DATAFILE)
    nncdf = nnc2df(eclfiles, pillars=args.pillars)
    nncdf.to_csv(args.output, index=False)
    print("Wrote to " + args.output)
