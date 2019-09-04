#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract grid information from Eclipse output files as Dataframes.

Each cell in the grid correspond to one row.

For grid cells, x, y, z for cell centre and volume is available as
geometric information. Static data (properties) can be merged from
the INIT file, and dynamic data can be merged from the Restart (UNRST)
file.
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

from ecl.eclfile import EclFile
from .eclfiles import EclFiles


def rstdates(eclfiles):
    """Return a list of datetime objects for the available dates in the RST file"""
    report_indices = EclFile.file_report_list(eclfiles.get_rstfilename())
    return [
        eclfiles.get_rstfile().iget_restart_sim_time(index).date()
        for index in range(0, len(report_indices))
    ]


def dates2rstindices(eclfiles, dates):
    """Return the restart index/indices for a given datetime or list of datetimes

      date: datetime.date or list of datetime.date, must
            correspond to an existing date. If list, it
            forces dateinheaders to be True.
            Can also be string, then the mnenomics
            'first', 'last', 'all', are supported, or ISO
            date formats.


    Raises exception no dates are not found.

    Return: tuple, first element is
        list of integers, corresponding to restart indices. Length 1 or more.
        second element is list of corresponding datetime.date objecs.
    """
    availabledates = rstdates(eclfiles)

    supportedmnemonics = ["first", "last", "all"]

    # After this control block, chosendates is a list of dates
    # we should extract, and which exists in UNRST.
    if isinstance(dates, str):
        if dates not in supportedmnemonics:
            # Try to parse as ISO date:
            try:
                isodate = dateutil.parser.isoparse(dates).date()
            except ValueError:
                raise ValueError("date " + str(dates) + " not understood")
            if isodate not in availabledates:
                raise ValueError("date " + str(isodate) + " not found in UNRST file")
            else:
                chosendates = [isodate]
        else:
            if dates == "first":
                chosendates = [availabledates[0]]
            elif dates == "last":
                chosendates = [availabledates[-1]]
            elif dates == "all":
                chosendates = availabledates
    elif isinstance(dates, datetime.date):
        chosendates = [dates]
    elif isinstance(dates, datetime.datetime):
        chosendates = [dates.date()]
    elif isinstance(dates, list):
        chosendates = [x for x in dates if x in availabledates]
        if not chosendates:
            raise ValueError("None of the requested dates were found")
        elif len(chosendates) < len(availabledates):
            logger.warning("Not all dates found in UNRST\n")
    else:
        raise ValueError("date " + str(dates) + " not understood")

    rstindices = [availabledates.index(x) for x in chosendates]
    return (rstindices, chosendates)


def rst2df(eclfiles, date, dateinheaders=False):
    """Return a dataframe with dynamic data from the restart file
    for each cell, at a particular date.

    Args:
        eclfiles: EclFiles object
        date: datetime.date or list of datetime.date, must
            correspond to an existing date. If list, it
            forces dateinheaders to be True.
            Can also be string, then the mnenomics
            'first', 'last', 'all', are supported, or ISO
            date formats.
        dateinheaders: boolean on whether the date should
            be added to the column headers. Instead of
            SGAS as a column header, you get SGAS@YYYY-MM-DD.
    """
    # First task is to determine the restart index to extract
    # data for:
    (rstindices, chosendates) = dates2rstindices(eclfiles, date)

    logging.info("Extracting restart information at dates {}".format(str(chosendates)))

    # Determine the available restart vectors, we only include
    # those with correct length, meaning that they are defined
    # for all active cells:
    activecells = eclfiles.get_egrid().getNumActive()
    rstvectors = []
    for vec in eclfiles.get_rstfile().headers:
        if vec[1] == activecells:
            rstvectors.append(vec[0])
    rstvectors = list(set(rstvectors))  # Make unique list
    # Note that all of these might not exist at all timesteps.

    rst_dfs = []
    for rstindex in rstindices:
        # Filter the rst vectors once more, all of them
        # might not be available at all timesteps:
        present_rstvectors = []
        for vec in rstvectors:
            if eclfiles.get_rstfile().iget_named_kw(vec, rstindex):
                present_rstvectors.append(vec)

        if not present_rstvectors:
            logging.warning("No restart vectors available at index {}".format(rstindex))
            continue

        # Make the dataframe
        rst_df = pd.DataFrame(
            columns=rstvectors,
            data=np.hstack(
                [
                    eclfiles.get_rstfile()
                    .iget_named_kw(vec, rstindex)
                    .numpyView()
                    .reshape(-1, 1)
                    for vec in present_rstvectors
                ]
            ),
        )

        # Tag the column names if requested, or if multiple rst indices
        # are asked for
        if dateinheaders or len(rstindices) > 1:
            datestr = "@" + chosendates[rstindices.index(rstindex)].isoformat()
            rst_df.columns = [colname + datestr for colname in rst_df.columns]

        rst_dfs.append(rst_df)

    if not rst_dfs:
        return pd.DataFrame()

    return pd.concat(rst_dfs, axis=1)


def gridgeometry2df(eclfiles):
    """Produce a Pandas Dataframe with Eclipse gridgeometry

    Order is significant, and is determined by the order from libecl, and used
    when merging with other dataframes with cell-data.

    Args:
        eclfiles (EclFiles): object holding the Eclipse output files.

    Returns:
        DataFrame: With columns I, J, K, X, Y, Z, VOLUME, one row pr. cell.
    """
    if not eclfiles:
        raise ValueError
    egrid_file = eclfiles.get_egridfile()
    grid = eclfiles.get_egrid()

    if not egrid_file or not grid:
        raise ValueError("No EGRID file supplied")

    logging.info("Extracting grid geometry from {}".format(egrid_file))
    index_frame = grid.export_index(active_only=True)
    ijk = index_frame.values[:, 0:3] + 1  # ijk from ecl.grid is off by one

    xyz = grid.export_position(index_frame)
    vol = grid.export_volume(index_frame)
    grid_df = pd.DataFrame(
        index=index_frame["active"],
        columns=["i", "j", "k", "x", "y", "z", "volume"],
        data=np.hstack((ijk, xyz, vol.reshape(-1, 1))),
    )
    # Type conversion, hstack maybe ruined the datatypes..
    grid_df["i"] = grid_df["i"].astype(int)
    grid_df["j"] = grid_df["j"].astype(int)
    grid_df["k"] = grid_df["k"].astype(int)

    # Column names should be uppercase
    grid_df.columns = [x.upper() for x in grid_df.columns]

    return grid_df


def init2df(init, active_cells, vectors=None):
    """Extract information from INIT file with cell data

    Order is significant, as index is used for merging

    Args:
        init_file: EclFile for the INIT object
        active_cells: int, The number of active cells each vector is required to have
            Other vectors will be dropped.
        vectors: List of vectors to include, glob-style wildcards supported
    """
    if not vectors:
        vectors = "*"  # This will include everything
    if not isinstance(vectors, list):
        vectors = [vectors]
    logging.info("Extracting vectors {} from INIT file".format(str(vectors)))

    # Build list of vector names to include:
    usevectors = []
    for vec in init.headers:
        if vec[1] == active_cells and any(
            [fnmatch.fnmatch(vec[0], key) for key in vectors]
        ):
            usevectors.append(vec[0])

    init_df = pd.DataFrame(
        columns=usevectors,
        data=np.hstack(
            [
                init.iget_named_kw(vec, 0).numpyView().reshape(-1, 1)
                for vec in usevectors
            ]
        ),
    )
    return init_df


def merge_gridframes(grid_df, init_df, rst_df):
    """Merge dataframes with grid data"""
    merged = pd.concat([grid_df, init_df, rst_df], axis=1, sort=False)
    return merged


def fill_parser(parser):
    """Set up sys.argv parser.

    Arguments:
        parser: argparse.ArgumentParser or argparse.subparser
    """
    parser.add_argument(
        "DATAFILE",
        help="Name of Eclipse DATA file. " + "INIT and EGRID file must lie alongside.",
    )
    parser.add_argument(
        "--initkeys",
        nargs="+",
        help="INIT vector wildcards for vectors to include",
        default="*",
    )
    parser.add_argument(
        "--rstdate",
        type=str,
        help="Point in time to grab restart data from, "
        + "either 'first' or 'last', or a date in "
        + "YYYY-MM-DD format",
        default="",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file.",
        default="eclgrid.csv",
    )
    parser.add_argument(
        "--dropconstants",
        action="store_true",
        help="Drop constant columns from the dataset",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def dropconstants(df, alwayskeep=None):
    """Drop/delete constant columns from a dataframe.

    Args:
        df: pd.DataFrame
        alwayskeep: string or list of strings of columns to keep
           anyway.
    Returns:
        pd.DataFrame with equal or less columns.
   """
    if not alwayskeep:
        alwayskeep = []
    if isinstance(alwayskeep, str):
        alwayskeep = [alwayskeep]
    if not isinstance(alwayskeep, list):
        raise TypeError("alwayskeep must be a list")
    if not isinstance(df, pd.DataFrame):
        raise TypeError("dropconstants() needs a dataframe")
    if df.empty:
        return df

    columnstodelete = []
    for col in set(df.columns) - set(alwayskeep):
        if len(df[col].unique()) == 1:
            columnstodelete.append(col)
    if columnstodelete:
        logging.info("Deleting constant columns {}".format(str(columnstodelete)))
    return df.drop(columnstodelete, axis=1)


def main():
    """Entry-point for module, for command line utility.
    """
    logging.warning("grid2csv is deprecated, use 'ecl2csv grid <args>' instead")
    parser = argparse.ArgumentParser()
    parser = fill_parser(parser)
    args = parser.parse_args()
    grid2df_main(args)


def grid2df_main(args):
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    gridgeom = gridgeometry2df(eclfiles)
    initdf = init2df(
        eclfiles.get_initfile(),
        eclfiles.get_egrid().getNumActive(),
        vectors=args.initkeys,
    )
    if args.rstdate:
        rst_df = rst2df(eclfiles, args.rstdate)
    else:
        rst_df = pd.DataFrame()
    grid_df = merge_gridframes(gridgeom, initdf, rst_df)
    if args.dropconstants:
        grid_df = dropconstants(grid_df)
    if args.output == "-":
        # Ignore pipe errors when writing to stdout.
        from signal import signal, SIGPIPE, SIG_DFL

        signal(SIGPIPE, SIG_DFL)
        grid_df.to_csv(sys.stdout, index=False)
    else:
        grid_df.to_csv(args.output, index=False)
        print("Wrote to " + args.output)
