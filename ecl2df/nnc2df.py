#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract NNC information from Eclipse output files.

NNC = Non Neighbour Connection

Inspired by https://github.com/equinor/libecl/blob/master/python/docs/examples/cmp_n    nc.py
"""
from __future__ import print_function

import os
import argparse
import pandas as pd

from ecl.eclfile import EclFile
from ecl.grid import EclGrid


def data2eclfiles(eclbase):
    """Loads INIT and GRID files from the supplied eclbase

    The eclbase should be the path to the Eclipse DATA file,
    with or without the .DATA extension

    Returns:
        tuple with EclFile from EGRID, EclGrid from EGRID
            and EclFile from INIT.
    """

    def rreplace(pat, sub, string):
        return string[0 : -len(pat)] + sub if string.endswith(pat) else string

    eclbase = rreplace(".DATA", "", eclbase)
    eclbase = rreplace(".", "", eclbase)

    egridfilename = eclbase + ".EGRID"
    initfilename = eclbase + ".INIT"

    if not os.path.exists(egridfilename):
        raise IOError(egridfilename + " not found")
    if not os.path.exists(initfilename):
        raise IOError(initfilename + " not found")

    return (EclFile(egridfilename), EclGrid(egridfilename), EclFile(initfilename))


def nnc2df(eclfiles):
    """Produce a Pandas Dataframe with NNC information

    A NNC is a pair of cells that are not next to each other
    in the index space (I, J, K), and are associated to a
    non-zero transmissibility.

    Columns: I1, J1, K1 (first cell in cell pair)
    I2, J2, K2 (second cell in cell pair), TRAN (transmissibility
    between the two cells)

    Args:
        eclfiles: tuple with EclFile (EGRID), EclGrid (EGRID) and EclFile (INIT)

    Returns:
        pd.DataFrame. Empty if no NNC information found.
    """
    egrid_file = eclfiles[0]
    egrid_grid = eclfiles[1]
    init_file = eclfiles[2]

    if not ("NNC1" in egrid_file and "NNC2" in egrid_file):
        print("No NNC data in EGRID")
        return pd.DataFrame()

    # Grid indices for first cell in cell pairs:
    nnc1 = egrid_file["NNC1"][0].numpy_view().reshape(-1, 1)
    nnc1_df = pd.DataFrame(
        columns=["I1", "J1", "K1"], data=[egrid_grid.get_ijk(x) for x in nnc1]
    )

    # Grid indices for second cell in cell pairs
    nnc2 = egrid_file["NNC2"][0].numpy_view().reshape(-1, 1)
    nnc2_df = pd.DataFrame(
        columns=["I2", "J2", "K2"], data=[egrid_grid.get_ijk(x) for x in nnc2]
    )

    # Obtain transmissibility values, corresponding to the cell pairs above.
    tran = init_file["TRANNNC"][0].numpy_view().reshape(-1, 1)
    tran_df = pd.DataFrame(columns=["TRAN"], data=tran)

    return pd.concat([nnc1_df, nnc2_df, tran_df], axis=1)


# Remaining functions are for the command line interface


def parse_args():
    """Parse sys.argv using argparse"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "DATAFILE",
        help="Name of Eclipse DATA file. " + "INIT and EGRID file must lie alongside.",
    )
    parser.add_argument(
        "-o", "--output", type=str, help="name of output csv file.", default="nnc.csv"
    )
    # args.add_argument("--augment", action='store_true',
    #    (TODO)       help="Add extra data for the cells in the cell pair")
    return parser.parse_args()


def main():
    """Entry-point for module, for command line utility"""
    args = parse_args()
    eclfiles = data2eclfiles(args.DATAFILE)
    nncdf = nnc2df(eclfiles)
    nncdf.to_csv(args.output, index=False)
    print("Wrote to " + args.output)
