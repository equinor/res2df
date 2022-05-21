"""Aggregates completion data from layer to zone"""

import argparse
import logging
from pathlib import Path
from typing import Any, List

import pandas as pd

from ecl2df import compdat, getLogger_ecl2csv
from ecl2df.eclfiles import EclFiles

from .common import write_dframe_stdout_file

logger = logging.getLogger(__name__)


def df(eclfiles: EclFiles, zonemap_filename: str) -> pd.DataFrame:
    """Info"""
    compdat_df = compdat.df(eclfiles, zonemap_filename=zonemap_filename)

    records = []
    for (well, zone, date), group_df in compdat_df.groupby(["WELL", "ZONE", "DATE"]):
        open_compl_df = group_df[group_df["OP/SH"] == "OPEN"]
        has_open_compl = open_compl_df.shape[0] > 0
        records.append(
            {
                "WELL": well,
                "ZONE": zone,
                "DATE": date,
                "KH": open_compl_df["KH"].sum() if has_open_compl else 0,
                "OP/SH": "OPEN" if has_open_compl else "SHUT",
            }
        )
    return pd.DataFrame(records)


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser: parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE",
        type=str,
        help="Name of Eclipse DATA file. " + "UNSMRY file must lie alongside.",
    )
    parser.add_argument(
        "--zonemap",
        type=str,
        help=("Name of lyr file with layer->zone mapping"),
        default="rms/output/zone/simgrid_zone_layer_mapping.lyr",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=(
            "Name of output csv file. Use '-' to write to stdout. "
            "Default 'well_completion_data.csv'"
        ),
        default="well_completion_data.csv",
    )
    parser.add_argument(
        "--use_wellconnstatus",
        action="store_true",
        help="Use well connection status extracted from CPI* summary data.",
    )
    parser.add_argument("--arrow", action="store_true", help="Write to pyarrow format")
    return parser


def wellcompletiondata_main(args):
    """Entry-point for module, for command line utility"""
    logger = getLogger_ecl2csv(__name__, vars(args))
    eclfiles = EclFiles(args.DATAFILE)

    if not Path(args.zonemap).is_file():
        raise FileNotFoundError(f"{args.zonemap} does not exists.")

    wellcompletiondata_df = df(eclfiles, args.zonemap)
    write_dframe_stdout_file(
        wellcompletiondata_df, args.output, index=False, caller_logger=logger
    )
