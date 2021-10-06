#!/usr/bin/env python
"""
Extract transmissibility information from Eclipse output files as Dataframes.
"""
import argparse
import logging
from typing import List, Union

import pandas as pd

import ecl2df.grid
import ecl2df.nnc
from ecl2df import getLogger_ecl2csv
from ecl2df.common import write_dframe_stdout_file

from .eclfiles import EclFiles

try:
    import networkx

    HAVE_NETWORKX = True
except ImportError:
    HAVE_NETWORKX = False

logger = logging.getLogger(__name__)


def df(
    eclfiles: EclFiles,
    vectors: Union[str, List[str]] = None,
    boundaryfilter: bool = False,
    group: bool = False,
    coords: bool = False,
    onlykdir: bool = False,
    onlyijdir: bool = False,
    addnnc: bool = False,
) -> pd.DataFrame:
    """Make a dataframe of the neighbour transmissibilities.

    The TRANX, TRANY and TRANZ (whenever nonzero) will be used
    to produce a row representing a cell-pair where there is
    transmissibility.

    You will get a dataframe with the columns::

        I1, J1, K1, I2, J2, K2, DIR, TRAN

    similar to what you get from non-neighbour connection export.

    If you ask for coordinates, you will also get the distance (DX,
    DY, DZ) for each connection.

    The DIR column indicates the direction, and can take the
    string values I, J or K.

    If you ask for additional vectors, like FIPNUM, then
    you will get a corresponding FIPNUM1 and FIPNUM2 added.

    Args:
        eclfiles: An object representing your Eclipse run
        vectors: Eclipse INIT vectors that you want to include
        boundaryfilter: Set to true if you want to filter where one INIT
            vector change. Only use for integer INIT vectors.
        group: Set to true if you want to sum transmissibilities over
            boundary interfaces. Implies boundaryfilter and requires only one integer
            INIT vector.
        coords: Set to true if you want to add coordinates for the
            average of the two cells centerpoint and the distance between
            the two cells centerpoints (X, Y, Z, DX, DY, DZ)
        onlykdir: Set to true if you only want transmissibilities in
            K direction
        onlyijdir: Set to true if you only want transmissibilities
            in the IJ-plane
        addnnc: Set to true if NNC connection should be concatenated to
            the dataframe

    Returns:
        Dataframe with one cell-pair pr. row. Empty dataframe if error.
    """
    if not vectors:
        vectors = []
    if not isinstance(vectors, list):
        vectors = [vectors]

    if group:
        # grouping implies boundaryfilter
        boundaryfilter = True

    if boundaryfilter and len(vectors) > 1:
        logger.error(
            "Can't filter to boundaries when more than one INIT vector is supplied"
        )
        return pd.DataFrame()

    if group and len(vectors) > 1:
        logger.error("Can't group to more than one INIT vector at a time")
        return pd.DataFrame()

    if onlykdir and onlyijdir:
        logger.warning(
            "Filtering to both k and to ij simultaneously results in empty dataframe"
        )

    grid_df = ecl2df.grid.df(eclfiles)
    existing_vectors = [vec for vec in vectors if vec in grid_df.columns]
    if len(existing_vectors) < len(vectors):
        logger.warning(
            "Vectors %s not found, skipping", str(set(vectors) - set(existing_vectors))
        )
    vectors = existing_vectors
    logger.info("Building transmissibility dataframe")
    if not onlykdir:
        tranx = pd.DataFrame(grid_df[grid_df["TRANX"] > 0][["I", "J", "K", "TRANX"]])
        tranx.rename(
            columns={"I": "I1", "J": "J1", "K": "K1", "TRANX": "TRAN"}, inplace=True
        )
        tranx["I2"] = tranx["I1"] + 1
        tranx["J2"] = tranx["J1"]
        tranx["K2"] = tranx["K1"]
        tranx["DIR"] = "I"
    else:
        tranx = pd.DataFrame()

    if not onlykdir:
        trany = pd.DataFrame(grid_df[grid_df["TRANY"] > 0][["I", "J", "K", "TRANY"]])
        trany.rename(
            columns={"I": "I1", "J": "J1", "K": "K1", "TRANY": "TRAN"}, inplace=True
        )
        trany["I2"] = trany["I1"]
        trany["J2"] = trany["J1"] + 1
        trany["K2"] = trany["K1"]
        trany["DIR"] = "J"
    else:
        trany = pd.DataFrame()

    if not onlyijdir:
        tranz = pd.DataFrame(grid_df[grid_df["TRANZ"] > 0][["I", "J", "K", "TRANZ"]])
        tranz.rename(
            columns={"I": "I1", "J": "J1", "K": "K1", "TRANZ": "TRAN"}, inplace=True
        )
        tranz["I2"] = tranz["I1"]
        tranz["J2"] = tranz["J1"]
        tranz["K2"] = tranz["K1"] + 1
        tranz["DIR"] = "K"
    else:
        tranz = pd.DataFrame()

    trans_df = pd.concat([tranx, trany, tranz], axis=0, sort=False)

    if addnnc:
        logger.info("Adding NNC data")
        nnc_df = ecl2df.nnc.df(eclfiles, coords=False, pillars=False)
        nnc_df["DIR"] = "NNC"
        trans_df = pd.concat([trans_df, nnc_df], sort=False)

    # If we have additional vectors we want, merge them in:
    vectorscoords = list(vectors)  # Copy
    if coords:
        if "X" not in vectorscoords:
            vectorscoords.append("X")
        if "Y" not in vectorscoords:
            vectorscoords.append("Y")
        if "Z" not in vectorscoords:
            vectorscoords.append("Z")

    if vectorscoords:
        logger.info("Adding vectors %s", str(vectorscoords))
        grid_df = grid_df.reset_index()
        trans_df = pd.merge(
            trans_df,
            grid_df[["I", "J", "K"] + vectorscoords],
            left_on=["I1", "J1", "K1"],
            right_on=["I", "J", "K"],
        )
        trans_df = trans_df.drop(["I", "J", "K"], axis=1)
        trans_df = pd.merge(
            trans_df,
            grid_df[["I", "J", "K"] + vectorscoords],
            left_on=["I2", "J2", "K2"],
            right_on=["I", "J", "K"],
            suffixes=("1", "2"),
        )
        trans_df = trans_df.drop(["I", "J", "K"], axis=1)

    if coords:
        trans_df["X"] = (trans_df["X1"] + trans_df["X2"]) / 2.0
        trans_df["Y"] = (trans_df["Y1"] + trans_df["Y2"]) / 2.0
        trans_df["Z"] = (trans_df["Z1"] + trans_df["Z2"]) / 2.0
        trans_df["DX"] = abs(trans_df["X1"] - trans_df["X2"])
        trans_df["DY"] = abs(trans_df["Y1"] - trans_df["Y2"])
        trans_df["DZ"] = abs(trans_df["Z1"] - trans_df["Z2"])
        trans_df = trans_df.drop(["X1", "X2", "Y1", "Y2", "Z1", "Z2"], axis=1)

    if boundaryfilter:
        assert len(vectors) == 1
        logger.info(
            "Filtering to transmissibilities crossing different %s values", vectors[0]
        )
        vec1 = vectors[0] + "1"
        vec2 = vectors[0] + "2"
        trans_df = trans_df[(trans_df[vec1] != trans_df[vec2])]

    if group:
        assert len(vectors) == 1  # This is checked above
        assert boundaryfilter
        logger.info("Grouping transmissiblity over %s interfaces", str(vectors[0]))
        vec1 = vectors[0] + "1"
        vec2 = vectors[0] + "2"
        pairname = vectors[0] + "PAIR"
        # Construct a column with values like "3-4" for a pair
        # where FIPNUM1 is 4 and FIPNUM2 is 3
        trans_df[pairname] = [
            str(int(min(x[1:3]))) + "-" + str(int(max(x[1:3])))
            for x in trans_df[[vec1, vec2]].itertuples()
        ]

        aggregators = {
            "X": "mean",
            "Y": "mean",
            "Z": "mean",
            "DX": "mean",
            "DY": "mean",
            "DZ": "mean",
            "TRAN": "sum",
        }
        aggregators = {
            key: value for (key, value) in aggregators.items() if key in trans_df
        }
        trans_df = trans_df.groupby(pairname).agg(aggregators).reset_index()

        # Reinstate FIPNUM1 and FIPNUM2 (by splitting the pair, to get sorting for free)
        vectuples = trans_df[pairname].str.split("-")
        trans_df[vec1] = [tup[0] for tup in vectuples]
        trans_df[vec2] = [tup[1] for tup in vectuples]

    return trans_df


def make_nx_graph(eclfiles: EclFiles, region: str = "FIPNUM") -> "networkx.Graph":
    """Construct a networkx graph for the transmissibilities."""
    if not HAVE_NETWORKX:
        logger.error("Please install networkx for this function to work")
        return None
    trans_df = df(eclfiles, vectors=[region], coords=True, group=True)
    reg1 = region + "1"
    reg2 = region + "2"
    graph = networkx.Graph()
    graph.add_weighted_edges_from(
        [tuple(row) for row in trans_df[[reg1, reg2, "TRAN"]].values]
    )
    return graph


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
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
        "--boundaryfilter",
        action="store_true",
        help=(
            "Filter to connections where the INIT vector change value. "
            "Only one INIT vector allowed."
        ),
    )
    parser.add_argument(
        "--onlyk", action="store_true", help="Filter to only K direction"
    )
    parser.add_argument("--onlyij", action="store_true", help="Filter to only IJ-plane")
    parser.add_argument(
        "--coords", action="store_true", help="Add coordinates to dataframe"
    )
    parser.add_argument(
        "--group",
        action="store_true",
        help=(
            "Group transmissibilities over region "
            "interfaces. Specify the region name in --vectors"
        ),
    )
    parser.add_argument(
        "--nnc",
        action="store_true",
        help="Add NNC transmissibilities to the same dataframe",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file. Use '-' for stdout",
        default="trans.csv",
    )
    return parser


def trans_main(args):
    """This is the command line API"""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    eclfiles = EclFiles(args.DATAFILE)
    trans_df = df(
        eclfiles,
        vectors=args.vectors,
        boundaryfilter=args.boundaryfilter,
        onlykdir=args.onlyk,
        onlyijdir=args.onlyij,
        coords=args.coords,
        group=args.group,
        addnnc=args.nnc,
    )

    write_dframe_stdout_file(trans_df, args.output, index=False, caller_logger=logger)
