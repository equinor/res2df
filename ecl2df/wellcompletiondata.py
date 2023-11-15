"""Aggregates completion data from layer to zone"""

import argparse
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import pyarrow
import pyarrow.feather

from ecl2df import common, compdat, getLogger_ecl2csv, wellconnstatus
from ecl2df.eclfiles import EclFiles

from .common import write_dframe_stdout_file

logger = logging.getLogger(__name__)


class EclipseUnitSystem(str, Enum):
    METRIC = "METRIC"
    FIELD = "FIELD"
    LAB = "LAB"
    PVTM = "PVT-M"


class KHUnit(Enum):
    METRIC = "mDm"
    FIELD = "mDft"
    LAB = "mDcm"
    PVTM = "mDm"


def df(
    eclfiles: EclFiles,
    zonemap: Dict[int, str],
    use_wellconnstatus: bool = False,
    excl_well_startswith: Optional[str] = None,
) -> pd.DataFrame:
    """Aggregates compdat to zone level. If use_wellconnstatus is True,
    the actual OP/SH status of a connection will be extracted from summary
    data using the wellconnstatus module. If not, connection status is taken
    directly from parsing the schedule file, using the compdat module.

    The aggregation is done according to the following rules. A zone is
    regarded as open if one or more connections are open, regardless of
    if other connections are closed. And the KH is summed over open connections
    only.

    Args:
        eclfiles; EclFiles object
        zonemap: dictionary with layer->zone mapping
        use_wellconnstatus: boolean

    Returns:
        pd.DataFrame with one row per unique combination of well, zone and date.
    """
    compdat_df = compdat.df(eclfiles, zonemap=zonemap)
    if "ZONE" not in compdat_df.columns:
        logger.warning(
            "ZONE column not generated in compdat table. "
            "Empty dataframe will be returned."
            f"Zonemap used: {zonemap}"
        )
        return pd.DataFrame()

    # Filter only the columns needed.
    compdat_df = compdat_df[["DATE", "WELL", "I", "J", "K1", "OP/SH", "KH", "ZONE"]]
    # Convert DATE column to datetime format
    compdat_df["DATE"] = pd.to_datetime(compdat_df["DATE"])

    # If excl_well_startswith is not None, filter out wells that starts with this
    if excl_well_startswith is not None:
        compdat_df = _excl_well_startswith(compdat_df, excl_well_startswith)

    if use_wellconnstatus:
        wellconnstatus_df = wellconnstatus.df(eclfiles)
        compdat_df = _merge_compdat_and_connstatus(compdat_df, wellconnstatus_df)

    compdat_df = _aggregate_layer_to_zone(compdat_df)

    # Add metadata as an attribute the dataframe
    meta = _get_metadata(eclfiles)
    # Slice meta to dataframe columns:
    compdat_df.attrs["meta"] = {
        column_key: meta[column_key] for column_key in compdat_df if column_key in meta
    }

    return compdat_df


def _get_ecl_unit_system(eclfiles: EclFiles) -> EclipseUnitSystem:
    """Returns the unit system of an eclipse deck. The options are \
    METRIC, FIELD, LAB and PVT-M.

    If none of these are found, the function returns METRIC which is the
    default unit system in Eclipse.
    """
    unit_systems = [unitsystem.value for unitsystem in EclipseUnitSystem]
    for keyword in eclfiles.get_ecldeck():
        if keyword.name in unit_systems:
            return EclipseUnitSystem(keyword.name)
    return EclipseUnitSystem.METRIC


def _get_metadata(eclfiles: EclFiles) -> Dict[str, Dict[str, Any]]:
    """Provide metadata for the well completion data export"""
    meta: Dict[str, Dict[str, str]] = {}
    unitsystem = _get_ecl_unit_system(eclfiles)
    kh_units = {
        EclipseUnitSystem.METRIC: KHUnit.METRIC,
        EclipseUnitSystem.FIELD: KHUnit.FIELD,
        EclipseUnitSystem.LAB: KHUnit.LAB,
        EclipseUnitSystem.PVTM: KHUnit.PVTM,
    }
    meta["KH"] = {}
    meta["KH"]["unit"] = kh_units[unitsystem].value
    return meta


def _excl_well_startswith(
    compdat_df: pd.DataFrame, excl_well_startswith: str
) -> pd.DataFrame:
    """Filters out rows where the well name starts with a given string"""
    keep_wells = [
        well
        for well in compdat_df["WELL"].unique()
        if not well.startswith(excl_well_startswith)
    ]
    return compdat_df[compdat_df["WELL"].isin(keep_wells)]


def _aggregate_layer_to_zone(compdat_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates well completion data from layer to zone.

    Args:
        compdat_df: pd.DataFrame with compdat data. Must have the following columns:
        DATE, WELL, OP/SH, KH and ZONE

    Returns:
        pd.DataFrame with one row per unique combination of well, zone and date.

    """
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

    Args:
        compdat_df: pd.DataFrame with compdat data, from parsing the sch file
        wellconnstatus_df: pd.DataFrame with well connection status data, extracted
        from summary data

    Returns:
        pd.DataFrame with one row per unique combination of well, zone and date.
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


def _df2pyarrow(dframe: pd.DataFrame) -> pyarrow.Table:
    """Construct a pyarrow table from dataframe with well
    completion data.

    The index in the dataframe will be ignored

    32-bit types will be used for integers and floats
    """
    field_list: List[pyarrow.Field] = []
    for colname in dframe.columns:
        if "meta" in dframe.attrs and colname in dframe.attrs["meta"]:
            # Boolean objects in the metadata dictionary must be converted to bytes:
            field_metadata = {
                bytes(key, encoding="ascii"): bytes(str(value), encoding="ascii")
                for key, value in dframe.attrs["meta"][colname].items()
            }
        else:
            field_metadata = {}
        if colname == "DATE":
            dtype = pyarrow.timestamp("ms")
        elif pd.api.types.is_integer_dtype(dframe.dtypes[colname]):
            dtype = pyarrow.int32()
        elif pd.api.types.is_string_dtype(dframe.dtypes[colname]):
            dtype = pyarrow.string()
        else:
            dtype = pyarrow.float32()
        field_list.append(pyarrow.field(colname, dtype, metadata=field_metadata))

    schema = pyarrow.schema(field_list)
    return pyarrow.Table.from_pandas(dframe, schema=schema, preserve_index=False)


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
        default="well_completion_data",
    )
    parser.add_argument(
        "--use_wellconnstatus",
        action="store_true",
        help="Use well connection status extracted from CPI* summary data.",
    )
    parser.add_argument(
        "--excl_well_startswith",
        type=str,
        help="Exludes wells that starts with this string from the export.",
        default=None,
    )
    parser.add_argument("--arrow", action="store_true", help="Write to pyarrow format")
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def wellcompletiondata_main(args):
    """Entry-point for module, for command line utility"""
    logger = getLogger_ecl2csv(__name__, vars(args))

    eclfiles = EclFiles(args.DATAFILE)
    if not Path(args.zonemap).is_file():
        wellcompletiondata_df = pd.DataFrame()
        logger.info(f"Zonemap not found: {args.zonemap}")
    else:
        zonemap = common.convert_lyrlist_to_zonemap(common.parse_lyrfile(args.zonemap))
        wellcompletiondata_df = df(
            eclfiles, zonemap, args.use_wellconnstatus, args.excl_well_startswith
        )
        logger.info(
            f"Well completion data successfully generated with zonemap: {zonemap}"
        )

    if args.arrow:
        wellcompletiondata_df = _df2pyarrow(wellcompletiondata_df)

    write_dframe_stdout_file(
        wellcompletiondata_df, args.output, index=False, caller_logger=logger
    )
