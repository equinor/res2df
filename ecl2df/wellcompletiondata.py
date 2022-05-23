"""Aggregates completion data from layer to zone"""

import argparse
from pathlib import Path

import pandas as pd

from ecl2df import compdat, getLogger_ecl2csv, wellconnstatus
from ecl2df.eclfiles import EclFiles

from .common import write_dframe_stdout_file


def df(
    eclfiles: EclFiles, zonemap_filename: str, use_wellconnstatus: bool
) -> pd.DataFrame:
    """Info"""
    compdat_df = compdat.df(eclfiles, zonemap_filename=zonemap_filename)[
        ["DATE", "WELL", "I", "J", "K1", "OP/SH", "KH", "ZONE"]
    ]
    compdat_df["DATE"] = pd.to_datetime(compdat_df["DATE"])

    if use_wellconnstatus:
        wellconnstatus_df = wellconnstatus.df(eclfiles)
        compdat_df = _merge_compdat_and_connstatus(compdat_df, wellconnstatus_df)

    return _aggregate_layer_to_zone(compdat_df)


def _aggregate_layer_to_zone(compdat_df: pd.DataFrame) -> pd.DataFrame:
    """Descr"""
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


def _merge_compdat_and_connstatus(
    compdat_df: pd.DataFrame, wellconnstatus_df: pd.DataFrame
) -> pd.DataFrame:
    """This function merges the compdat data with the well connection status data
    (extracted from the CPI summary data). The connection status data will be used
    for wells where it exists. The KH will be merged from the compdat. For wells
    that are not in the connection status data, the compdat data will be used as it is.

    This approach is fast, but a couple of things should be noted:
    * in the connection status data, a connection is not set to SHUT before it has been
    OPEN. In the compdat data, some times all connections are first defined and the
    opened later.
    * any connections that are in compdat but not in connections status will be ignored
    (e.g. connections that are always shut)
    * there is no logic to handle KH changing with time for the same connection (this
    can easily be added using apply in pandas, but it is very rare and slows down the
    function significantly)
    * if connection status is missing for a realization, but compdat exists, compdat
    will also be ignored.
    """
    match_on = ["WELL", "I", "J", "K1"]
    wellconnstatus_df.rename({"K": "K1"}, axis=1, inplace=True)

    dframe = pd.merge(
        wellconnstatus_df,
        compdat_df[match_on + ["KH", "ZONE"]],
        on=match_on,
        how="left",
    )

    # There will often be several rows (with different OP/SH) matching in compdat.
    # Only the first is kept
    dframe.drop_duplicates(subset=["DATE"] + match_on, keep="first", inplace=True)

    # Concat from compdat the wells that are not in well connection status
    dframe = pd.concat(
        [dframe, compdat_df[~compdat_df["WELL"].isin(dframe["WELL"].unique())]]
    )
    dframe = dframe.reset_index(drop=True)
    dframe["KH"] = dframe["KH"].fillna(0)
    return dframe


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

    wellcompletiondata_df = df(eclfiles, args.zonemap, args.use_wellconnstatus)
    write_dframe_stdout_file(
        wellcompletiondata_df, args.output, index=False, caller_logger=logger
    )
