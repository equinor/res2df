"""
Extract non-neighbour connection (NNC) information from Eclipse output files.
"""
import argparse
import datetime
import logging
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from ecl2df import EclFiles, __version__, common, getLogger_ecl2csv, grid
from ecl2df.common import write_dframe_stdout_file

logger: logging.Logger = logging.getLogger(__name__)


def df(eclfiles: EclFiles, coords: bool = False, pillars: bool = False) -> pd.DataFrame:
    """Produce a Pandas Dataframe with NNC information

    A NNC is a pair of cells that are not next to each other
    in the index space (I, J, K), and are associated to a
    non-zero transmissibility.

    Columns: I1, J1, K1 (first cell in cell pair)
    I2, J2, K2 (second cell in cell pair), TRAN (transmissibility
    between the two cells)

    Args:
        eclfiles: object that can serve EclFile and EclGrid
            on demand
        coords: Set to True if you want the midpoint of the two
            connected cells to be computed and added to the columns
            X, Y and Z.
        pillars: Set to True if you want to filter to vertical
            (along pillars) connections only.

    Returns:
        Empty if no NNC information found.
    """
    egrid_file = eclfiles.get_egridfile()
    egrid_grid = eclfiles.get_egrid()
    init_file = eclfiles.get_initfile()

    if not ("NNC1" in egrid_file and "NNC2" in egrid_file):
        logger.warning("No NNC data in EGRID")
        return pd.DataFrame()
    if "TRANNNC" not in init_file:
        logger.warning("No TRANNNC data in INIT (E300 parallell run?)")
        return pd.DataFrame()

    # Grid indices for first cell in cell pairs, into a vertical
    # vector. The indices are "global" in libecl terms, and are
    # 1-based (FORTRAN). Convert to zero-based before sending to get_ijk()
    nnc1 = egrid_file["NNC1"][0].numpy_view().reshape(-1, 1)
    logger.info(
        "NNC1: len: %d, min: %d, max: %d (global indices)",
        len(nnc1),
        min(nnc1),
        max(nnc1),
    )
    idx_cols1 = ["I1", "J1", "K1"]
    nnc1_df = pd.DataFrame(
        columns=idx_cols1,
        data=[egrid_grid.get_ijk(global_index=int(x) - 1) for x in nnc1],
    )
    # Returned indices from get_ijk are zero-based, convert to 1-based indices
    nnc1_df[idx_cols1] = nnc1_df[idx_cols1] + 1

    # Grid indices for second cell in cell pairs
    nnc2 = egrid_file["NNC2"][0].numpy_view().reshape(-1, 1)
    logger.info(
        "NNC2: len: %d, min: %d, max: %d (global indices)",
        len(nnc2),
        min(nnc2),
        max(nnc2),
    )
    idx_cols2 = ["I2", "J2", "K2"]
    nnc2_df = pd.DataFrame(
        columns=idx_cols2,
        data=[egrid_grid.get_ijk(global_index=int(x) - 1) for x in nnc2],
    )
    nnc2_df[idx_cols2] = nnc2_df[idx_cols2] + 1

    # Obtain transmissibility value, corresponding to the cell pairs above.
    tran = init_file["TRANNNC"][0].numpy_view().reshape(-1, 1)
    logger.info(
        "TRANNNC: len: %d, min: %f, max: %f, mean=%f",
        len(tran),
        min(tran),
        max(tran),
        tran.mean(),
    )
    tran_df = pd.DataFrame(columns=["TRAN"], data=tran)

    nncdf = pd.concat([nnc1_df, nnc2_df, tran_df], axis=1)
    if pillars:
        nncdf = filter_vertical(nncdf)
    if coords:
        nncdf = add_nnc_coords(nncdf, eclfiles)
    return nncdf


def add_nnc_coords(nncdf: pd.DataFrame, eclfiles: EclFiles) -> pd.DataFrame:
    """Add columns X, Y and Z for the connection midpoint

    This extracts x, y and z for (I1, J1, K1) and (I2, J2, K2)
    and computes the average in each direction.

    Arguments:
        nncdf: With grid index columns (I1, J1, K1, I2, J2, K2)
        eclfiles: Object used to fetch grid data from EGRID.

    Returns:
        Incoming dataframe augmented with the columns X, Y and Z.
    """
    gridgeometry = grid.gridgeometry2df(eclfiles)
    gnncdf = pd.merge(
        nncdf,
        gridgeometry,
        how="left",
        left_on=["I1", "J1", "K1"],
        right_on=["I", "J", "K"],
    )
    gnncdf = pd.merge(
        gnncdf,
        gridgeometry,
        how="left",
        left_on=["I2", "J2", "K2"],
        right_on=["I", "J", "K"],
        suffixes=("", "_2"),
    )
    # Use pd.DataFrame.mean for averaging, since it can ignore
    # NaN's. In case only one coordinate is NaN, we then get the other one.
    # (NaN coordinates are potentially from zero-volume cells?)
    gnncdf["X"] = gnncdf[["X", "X_2"]].mean(axis=1)
    gnncdf["Y"] = gnncdf[["Y", "Y_2"]].mean(axis=1)
    gnncdf["Z"] = gnncdf[["Z", "Z_2"]].mean(axis=1)

    # Let go of the temporary columns we have in gnncdf
    return gnncdf[list(nncdf.columns) + ["X", "Y", "Z"]]


def filter_vertical(nncdf: pd.DataFrame) -> pd.DataFrame:
    """Filter to vertical connections

    Arguments:
        nncdf: A dataframe with the columns
            I1, J1, K1, I2, J2, K2.

    Returns:
        Filtered copy of incoming dataframe.
    """
    prelen = len(nncdf)
    vnncdf = nncdf[nncdf["I1"] == nncdf["I2"]]
    vnncdf = vnncdf[vnncdf["J1"] == vnncdf["J2"]]
    postlen = len(vnncdf)
    logger.info(
        "Filtered to vertical connections, %d removed, %d connections kept",
        prelen - postlen,
        postlen,
    )
    return vnncdf


# Remaining functions are for the command line interface


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parser

    Arguments:
        parser: argparse.ArgumentParser or argparse.subparser
    """
    parser.add_argument(
        "DATAFILE",
        help="Name of Eclipse DATA file. " + "INIT and EGRID file must lie alongside.",
    )
    parser.add_argument(
        "-c",
        "--coords",
        action="store_true",
        help="Add xyz coords of connection midpoint",
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
    return parser


def df2ecl_editnnc(
    nnc_df: pd.DataFrame, filename: Optional[str] = None, nocomments: bool = False
) -> str:
    """Write an EDITNNC keyword

    This will write::

        EDITNNC
           IX IY IZ JX JY JZ TRANM /
           ...
        /

    and return as string and/or dump to filename.

    The column TRANM must be in the incoming dataframe
    and it should be the multiplier to be written for
    each connection.

    If you want to edit only a subset of the non-neighbour
    connections, filter the dataframe upfront.

    Only rows where the column "DIR" is "NNC" will be considered.

    Args:
        nnc_df (pd.DataFrame): Dataframe with I1, J1, K1, I2, J2, K2 and a TRANM
            column, where the multiplier to be written is in TRANM. If the DIR
            column is present, only the rows with 'NNC' in the DIR column
            are included.
        filename (str): Filename to write to
        nocomments (bool): Set to True if you don't want any comments
            in the produced string/file

    Returns:
        string with the EDITNNC keyword.
    """

    string = ""
    ecl2df_header = (
        "Output file printed by ecl2df.nnc"
        + " "
        + __version__
        + "\n"
        + " at "
        + str(datetime.datetime.now())
    )
    if not nocomments:
        string += common.comment_formatter(ecl2df_header)
    string += "\n"

    if "DIR" in nnc_df:
        nnc_df = nnc_df[nnc_df["DIR"] == "NNC"]

    if "TRANM" not in nnc_df:
        raise ValueError("TRANM not supplied in nnc_df")
    string += "EDITNNC" + os.linesep
    table_str = nnc_df[["I1", "J1", "K1", "I2", "J2", "K2", "TRANM"]].to_string(
        header=True, index=False
    )
    lines = table_str.rstrip().split(os.linesep)
    indent = "   "
    string += "-- " + lines[0] + os.linesep
    string += os.linesep.join([indent + line + " /" for line in lines[1:]])
    string += os.linesep
    string += "/"
    if not nocomments:
        string += " "
        string += common.comment_formatter(
            f"  {len(nnc_df)} nnc connections, avg multiplier {nnc_df['TRANM'].mean()}"
        )
    string += "\n\n"

    if filename is not None:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        Path(filename).write_text(string, encoding="utf-8")
    return string


def nnc_main(args) -> None:
    """Command line access point from main() or from ecl2csv via subparser"""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    eclfiles = EclFiles(args.DATAFILE)
    nncdf = df(eclfiles, coords=args.coords, pillars=args.pillars)
    write_dframe_stdout_file(
        nncdf,
        args.output,
        index=False,
        caller_logger=logger,
        logstr=f"Wrote to {args.output}",
    )
    nncdf.to_csv(args.output, index=False)
