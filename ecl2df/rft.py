"""Converter module for Eclipse RFT output files to Pandas Dataframes

If MULTISEG wells are found, the segment data associated to
a connection is merged onto the same row as additional columns,
assuming connections do not point to more than one segment.

If ICD segments are detected (recognized as branches only containing
one segment), they are merged into the same row that already contains
connection data (CONxxxxx) and its segment data (now giving
information for the conditions in the tubing).

The columns representing SEGxxxxx data on ICD segments are renamed
by adding the prefix ``ICD_``
"""

import argparse
import collections
import datetime
import logging
from typing import Any, Dict, Iterable, Optional, Set

import numpy as np
import pandas as pd
from ecl.eclfile import EclFile

from ecl2df import getLogger_ecl2csv

from .common import merge_zones, write_dframe_stdout_file
from .eclfiles import EclFiles
from .gruptree import tree_from_dict

logger: logging.Logger = logging.getLogger(__name__)

# In debug mode, these columns will be exported to three csv files.
CON_TOPOLOGY_COLS: Set = {"CONIDX", "CONBRNO", "CONSEGNO", "CONNXT", "DEPTH"}
SEG_TOPOLOGY_COLS: Set = {
    "SEGIDX",
    "SEGIDX_upstream",
    "SEGBRNO",
    "SEGBRNO_upstream",
    "SEGNXT",
    "SEGNXT_upstream",
    "JUNCTION",
    "JUNCTION_downstream",
    "LONELYSEG",
    "LEAF",
    "SEGDEPTH",
}
ICD_TOPOLOGY_COLS: Set = {
    "ICD_SEGBRNO_upstream",
    "ICD_SEGIDX_upstream",
    "ICD_LEAF",
    "ICD_JUNCTION",
    "ICD_LONELYSEG",
    "ICD_JUNCTION_downstream",
    "ICD_SEGBRNO",
    "ICD_SEGNXT",
    "ICD_SEGIDX",
    "ICD_SEGDEPTH",
}


def _rftrecords2df(rftfile: EclFile) -> pd.DataFrame:
    """Construct a dataframe just for navigation on the RFT records,
    from the attribute 'headers' in EclFile object constructed from the
    binary RFT file

    The dataframe will consist of the columns and with example data:
        timeindex, recordidx, recordname, recordlength, recordtype
        0, 0, TIME, 1, REAL
        0, 1, DATE, 3, INTE
        0, 2, WELLETC, 16,  CHAR
        ...
        1, 30, TIME, 1, REAL
        1, 31, DATE, 3, INTE
        ....
        3, 89, SWAT, 14, REAL

    where the column recordidx refers to the RFT file such that
        rftfile[89] = EclKW(size=14, name="SWAT", ...)

    Args:
        rftfile (EclFile)
    """
    nav_df = pd.DataFrame(rftfile.headers)
    nav_df.columns = ["recordname", "recordlength", "recordtype"]
    nav_df["timeindex"] = np.nan
    # the TIME record (in recordname) signifies that the forthcoming records
    # belong to  this TIME value, and we make a new column in the header data that
    # tells us the row number for the associated TIME record
    nav_df.loc[nav_df["recordname"] == "TIME", "timeindex"] = nav_df[
        nav_df["recordname"] == "TIME"
    ].index
    nav_df.fillna(
        method="ffill", inplace=True
    )  # forward fill (because any record is associated to the previous TIME record)
    nav_df["timeindex"] = nav_df["timeindex"].astype(int)
    logger.info(
        "Located %s RFT headers at %s distinct dates",
        str(len(nav_df)),
        str(len(nav_df["timeindex"].unique())),
    )
    nav_df.index.name = "recordidx"
    return nav_df.reset_index()


def rftrecords(rftfile: EclFile) -> Iterable[Dict[str, Any]]:
    """Generator for looping over RFT records in a EclFile object.

    Each returned RFT record is represented as a dict with the keys:
        headers: pd.DataFrame, indexed by recordname

    Args:
        EclFile made from a binary RFT file.
    """
    navigation_frame = _rftrecords2df(rftfile)
    for timeindex, headers in navigation_frame.groupby("timeindex"):
        headers = headers.set_index("recordname")
        rftrecord = {}
        rftrecord["headers"] = headers
        # All rows in nav_record_df represents  the data in the current
        # RFT record
        dateidx = int(headers.loc["DATE"]["recordidx"])
        rftrecord["date"] = datetime.date(
            rftfile[dateidx][2], rftfile[dateidx][1], rftfile[dateidx][0]
        )
        rftrecord["wellname"] = rftfile[int(headers.loc["WELLETC"]["recordidx"])][
            1
        ].strip()

        rftrecord["wellmodel"] = rftfile[int(headers.loc["WELLETC"]["recordidx"])][
            6
        ].strip()
        # wellmodel is either "STANDARD" or "MULTISEG"

        rftrecord["timeindex"] = timeindex
        yield rftrecord


def get_con_seg_data(
    rftrecord: Dict[str, Any], rftfile: EclFile, datatype: str
) -> pd.DataFrame:
    """
    Build a dataframe of CON* or SEG* data for a specific RFT record,
    that is for one well at one date.

    Dataframe will for datatype=="CON" look like::

      DEPTH, SWAT, CONKH, CONIDX, ..
      2300,  0.3, 3000, 1
      2310, 0.2, 1231, 2

    and number of rows will equal the number of connected cells (COMPDAT lines)

    If it is for SEG data, all columns are prefixed by SEG
    and row count will be the number of segments defined in WELSEGS

    Args:
        rftrecord: Data for one RFT record, provided by rftrecords()
        rftfile:
        datatype: Either "CON" or "SEG"
    """
    if datatype not in ["CON", "SEG"]:
        raise ValueError("datatype must equal CON or SEG")

    headers = rftrecord["headers"]
    if datatype == "CON":
        rft_row_count = headers.loc["DEPTH"]["recordlength"]
    else:
        rft_row_count = headers.loc["SEGDEPTH"]["recordlength"]

    data_headers = headers[headers.recordlength == rft_row_count].reset_index()[
        ["recordidx", "recordname"]
    ]
    # If CON type, ensure, no SEG data included, and vice versa
    if datatype == "CON":
        data_headers = data_headers[~data_headers["recordname"].str.startswith("SEG")]
    else:
        data_headers = data_headers[data_headers["recordname"].str.startswith("SEG")]

    data = pd.DataFrame(
        {
            row["recordname"]: list(rftfile[row["recordidx"]])
            for _, row in data_headers.iterrows()
        }
    )

    # Ensure integer headers are integers:
    integer_columns = headers[headers["recordtype"] == "INTE"].index.values
    for col in (set(integer_columns) - {"DATE"}).intersection(
        set(data_headers["recordname"].values)
    ):
        data[col] = data[col].astype(int)
    data[datatype + "IDX"] = data.index + 1  # Add an index that starts with 1
    return data


def count_wellbranches(seg_data: pd.DataFrame) -> int:
    """From a segment dataframe, coming from get_con_seg_data(..., "SEG")
    determine the number of well branche.

    ICD segments must be split out first using split_seg_icd(), otherwise
    results are not reliable.

    Args:
        pd.DataFrame, with at least the columns SEGIDX, SEGNXT and SEGBRNO
    """
    if "LEAF" not in seg_data:
        seg_data = process_seg_topology(seg_data)

    branchcount = len(
        seg_data[~seg_data["LEAF"] | seg_data["JUNCTION_downstream"]]["SEGBRNO"]
        .dropna()
        .unique()
    )

    # logger.debug("Branches found: %d", count_wellbranches(merged))
    return max(1, branchcount)


def process_seg_topology(seg_data: pd.DataFrame) -> pd.DataFrame:
    """Determine and process the segment topology.

    The topology of the well segments are determined by the SEGNXT column in
    incoming dataframe, which corresponds to SEGIDX.

    SEGNXT points to the next segment downstream in a production well (and
    injector wells are treated as production here). Downstream is thus *upwards*
    in space, towards the sea.

    The last segment in a non-icd well gets the type TUBING.

    Args:
        seg_data: Segment structure defined as a table with at least
            the columns SEGIDX, SEGNXT

    Returns:
        Augmented dataframe, extra columns and perhaps extra rows.
    """
    if not {"SEGIDX", "SEGNXT"}.issubset(set(seg_data.columns)):
        raise ValueError("Insufficient topology columns in dataframe")

    seg_data = seg_data.sort_values("SEGIDX")
    # For the first segment, None is allowed as SEGNXT, which excludes
    # int as a  Pandas type. Convert to 0 for the moment
    seg_data["SEGNXT"] = seg_data["SEGNXT"].fillna(value=0).astype(int)

    # Outer merge first to add the upstream segment information to every row.
    merged = pd.merge(
        seg_data,
        seg_data,
        how="left",
        left_on="SEGIDX",
        right_on="SEGNXT",
        suffixes=("", "_upstream"),
    )
    del merged["SEGNXT_upstream"]
    # Later this might be changed to use the Pandas nullable integer type, but
    # using zero for NaN works in this context.
    merged["SEGIDX_upstream"] = merged["SEGIDX_upstream"].fillna(value=0).astype(int)
    merged["SEGBRNO_upstream"] = merged["SEGBRNO_upstream"].fillna(value=0).astype(int)

    # Now we can determine leaf segments by those with no extra information, since
    # we did an outer merge:
    merged["LEAF"] = merged["SEGIDX_upstream"].replace(0, np.nan).isnull()

    # Flag segments that have multiple upstream segments as junctions
    merged["JUNCTION"] = merged["SEGIDX"].duplicated(keep=False)

    # Determine if a segment is alone on its own branch
    merged["LONELYSEG"] = ~merged["SEGBRNO"].duplicated(keep=False)

    # We also want to flag the segment that is upstream a junction,
    merged["JUNCTION_downstream"] = False
    merged.loc[
        merged[merged["JUNCTION"]]["SEGIDX_upstream"], "JUNCTION_downstream"
    ] = True

    return merged


def seg2dicttree(seg_data: pd.DataFrame) -> dict:
    """Generate a nested dictionary representing the
    well through its segment topology

    Args:
        seg_data: topology determined by SEGIDX
            and SEGIDX_upstream

    Returns:
        Nested dict,
    """
    if seg_data.empty:
        return {}

    if "LEAF" not in seg_data:
        seg_data = process_seg_topology(seg_data)
    subtrees: dict = collections.defaultdict(dict)
    edges = []  # List of tuples
    for _, row in seg_data.iterrows():
        if "SEGIDX_upstream" in row and row["SEGIDX_upstream"] > 0:
            edges.append((row["SEGIDX_upstream"], row["SEGIDX"]))
    if not edges:
        return {seg_data["SEGIDX"].values[0]: {}}
    for child, parent in edges:
        subtrees[parent][child] = subtrees[child]

    children, parents = zip(*edges)
    roots = set(parents).difference(children)
    trees = []
    trees.append({root: subtrees[root] for root in roots})
    return trees[0]


def pretty_print_well(seg_data: pd.DataFrame) -> str:
    """Return a multiline string with the segment structure
    pretty printed as an ASCII tree.

    Args:
        seg_data: Segment dataframe

    Returns:
        Multiline string
    """
    dicttree = seg2dicttree(seg_data)
    return str(tree_from_dict(dicttree))


def split_seg_icd(seg_data: pd.DataFrame) -> pd.DataFrame:
    """Split a segment dataframe into a dataframe
    with non-ICD segments and one with.

    The segment properties (data) are merged into the downstream segments
    dataset, with the SEG prefixed switched to ICD.

    Returns:
        Dataframe with the ICD segments only. Empty if no ICDs found.
        and wider.
    """

    # Ensure we have some topology data present:
    if "LEAF" not in seg_data:
        seg_data = process_seg_topology(seg_data)

    icd_present = seg_data["SEGBRNO"].max() > count_wellbranches(seg_data)

    if not icd_present:
        return (seg_data, pd.DataFrame())

    # ICD segments are those where:
    #  * Leaf segments (connected reservoir / con_data row)
    #  # * Downstream segment is not a junction (because it must
    #    be connected to a tubing segment, which is again connected
    #    to a junction) (this might be too strict?)
    #    STOP: Cannot use this criteria, because junctions  due to ICDs
    #    are legit.
    #  * The segment must be on a branch with only one segment
    icd_seg_indices = seg_data[seg_data["LEAF"] & seg_data["LONELYSEG"]].index.values
    non_icd_seg_indices = seg_data[
        ~(seg_data["LEAF"] & seg_data["LONELYSEG"])
    ].index.values

    icd_seg_data = seg_data.reindex(icd_seg_indices)
    seg_data = seg_data.reindex(non_icd_seg_indices)

    icd_seg_data.columns = ["ICD_" + x for x in icd_seg_data.columns]

    logger.debug(
        "Found %d ICD segments, indices %s",
        len(icd_seg_data),
        str(icd_seg_data["ICD_SEGIDX"].values),
    )

    return (seg_data, icd_seg_data)


def merge_icd_seg_conseg(
    con_data: pd.DataFrame,
    seg_data: Optional[pd.DataFrame] = None,
    icd_data: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Merge ICD segments to the CONxxxxx data. We will be
    connection-centric in the outputted rows, that is
    one row pr. connection. If the setup is with more
    than one segment pr. connection (e.g. reservoir
    cell), then we would have to be smarter. Either
    averaging the properties, or be segment-centric in
    the output.

    Petrel happily puts many ICD segments to the same
    connection. This setup is a bug, with partially
    unknown effects when simulated in Eclipse. Should we
    warn the user??

    Args:
        con_data: Connection data (CONxxxx columns). One
            row pr. reservoir connection
        seg_data: Segment data, SEGxxxxx cols, one row pr. segment, and
            each segment should correspond to one ICD or to one reservoir connection.
            Supply empty or None if no segments found.
        icd_data: ICD data, ICD_SEGxxxx columns. One row pr
            ICD segment. One-to-one correspondence to con_data through ICD_SEGBRNO
            and CONBRNO required. Can be empty or None if no ICD present.
    """
    if seg_data is None:
        seg_data = pd.DataFrame()
    if icd_data is None:
        icd_data = pd.DataFrame()

    if logger.level <= logging.DEBUG:
        logger.debug("Writing connection data to con.csv")
        con_data[CON_TOPOLOGY_COLS.intersection(con_data.columns)].to_csv(
            "con.csv", index=False
        )
        logger.debug("Writing segment data to seg.csv")
        seg_data[SEG_TOPOLOGY_COLS.intersection(seg_data.columns)].to_csv(
            "seg.csv", index=False
        )
        logger.debug("Writing ICD data to icd.csv")
        icd_data[ICD_TOPOLOGY_COLS.intersection(icd_data.columns)].to_csv(
            "icd.csv", index=False
        )

    data = pd.DataFrame()
    if not icd_data.empty:
        # Merge ICD_* columns onto the dataframe representing reservoir
        # connections.
        data = pd.merge(con_data, icd_data, left_on="CONSEGNO", right_on="ICD_SEGIDX")

        # Merge SEGxxxxx to the dataframe with icd's and reservoir connections.
        assert not seg_data.empty

        data = pd.merge(
            data, seg_data, how="left", left_on="ICD_SEGNXT", right_on="SEGIDX"
        )

        # The merge has potentially included extra rows due to junctions.
        # After ICD merge, we can require that SEGIDX_upstream equals CONSEGNO
        data = data[data["CONSEGNO"] == data["SEGIDX_upstream"]]

        # Now the data for a reservoir connection, its ICD segment and the tubing
        #  segment is on the same row in the dataframe.

        # Gather connections that are not associated to ICDs:
        no_icd_con_segments = set(con_data["CONSEGNO"]) - set(icd_data["ICD_SEGIDX"])
        con_data_no_icd = (
            con_data.set_index("CONSEGNO").loc[no_icd_con_segments].reset_index()
        )
    else:
        con_data_no_icd = con_data

    if not seg_data.empty:
        data = pd.concat(
            [
                data,
                pd.merge(
                    con_data_no_icd, seg_data, left_on="CONSEGNO", right_on="SEGIDX"
                ),
            ],
            sort=False,
        )
    else:
        # Non-multisegment wells have only reservoir connection data.
        return con_data
    return data


def add_extras(dframe: pd.DataFrame, inplace: bool = True) -> pd.DataFrame:
    """Add extra nice-to-have columns to the dataframe
    with tubing, icd-segments, and reservoir  connections matched
    on rows

    Args:
        dframe: Dataframe typically obtained from merge_icd_seg()
        inplace: Set to False if the original should not be modified.

    Returns:
        The (possibly) augmented incoming dataframe.
    """
    if not inplace:
        dframe = dframe.copy()

    if "CONPRES" in dframe and "SEGPRES" in dframe:
        dframe["COMPLETION_DP"] = 0
        nonzero_pres = (dframe["CONPRES"] > 0) & (dframe["SEGPRES"] > 0)
        dframe.loc[nonzero_pres, "COMPLETION_DP"] = (
            dframe.loc[nonzero_pres, "CONPRES"] - dframe.loc[nonzero_pres, "SEGPRES"]
        )

    if not dframe.empty:
        dframe["DRAWDOWN"] = 0  # Set a default so that the column always exists

    if "CONPRES" in dframe and "PRESSURE" in dframe:
        nonzero_conpres = dframe["CONPRES"] > 0
        dframe.loc[nonzero_conpres, "DRAWDOWN"] = (
            dframe.loc[nonzero_conpres, "PRESSURE"]
            - dframe.loc[nonzero_conpres, "CONPRES"]
        )

    if "PRESSURE" in dframe:
        dframe["CONBPRES"] = dframe["PRESSURE"]  # Just an alias
    if "CONLENEN" in dframe and "CONLENST" in dframe:
        dframe["CONMD"] = 0.5 * (dframe["CONLENST"] + dframe["CONLENEN"])
        dframe["CONLENTH"] = dframe["CONLENEN"] - dframe["CONLENST"]

    if "CONORAT" in dframe and "CONLENTH" in dframe:
        dframe["CONORATS"] = dframe["CONORAT"] / dframe["CONLENTH"]
    if "CONWRAT" in dframe and "CONLENTH" in dframe:
        dframe["CONWRATS"] = dframe["CONWRAT"] / dframe["CONLENTH"]
    if "CONGRAT" in dframe and "CONLENTH" in dframe:
        dframe["CONGRATS"] = dframe["CONGRAT"] / dframe["CONLENTH"]

    return dframe


def df(
    eclfiles: EclFiles, wellname: Optional[str] = None, date: Optional[str] = None
) -> pd.DataFrame:
    """Loop over an RFT file and construct a dataframe representation
    of the data, ordered by well and date.

    Args:
        eclfiles: Object used to locate the RFT file
        wellname: If provided, only wells matching this string exactly
            will be included
        date: If provided, all other dates will be ignored. YYYY-MM-DD.
    """
    rftfile = eclfiles.get_rftfile()

    rftdata = []
    for rftrecord in rftrecords(rftfile):
        if wellname is not None and rftrecord["wellname"] != wellname:
            continue
        if date is not None and str(rftrecord["date"]) != date:
            continue

        logger.info(
            "Extracting %s well %s at %s, record index: %s",
            rftrecord["wellmodel"],
            str.rjust(rftrecord["wellname"], 8),
            rftrecord["date"],
            rftrecord["timeindex"],
        )

        headers = rftrecord["headers"]

        if "DEPTH" not in headers.index:
            logger.debug(
                "Well %s has no data to extract at %s",
                str(rftrecord["wellname"]),
                str(rftrecord["date"]),
            )
            continue

        con_data = get_con_seg_data(rftrecord, rftfile, "CON")

        # Process multisegment data (not necessarily the same number
        # of rows as the connection data). Data for segments
        # that are not associated with a connection will not be
        # included.

        has_seg_data = any(headers.index.str.startswith("SEG"))
        if rftrecord["wellmodel"] == "MULTISEG" and not has_seg_data:
            logger.warning(
                "Well %s is a multisegment well, but has no SEG data",
                rftrecord["wellname"],
            )
            # This should probably never happen (?)

        seg_data = pd.DataFrame()
        icd_data = pd.DataFrame()
        if has_seg_data:
            seg_data = get_con_seg_data(rftrecord, rftfile, "SEG")

            # For each downstream segment, merge in the data for its
            # upstream segment, and determine leaf nodes:
            seg_data = process_seg_topology(seg_data)
            logger.debug(pretty_print_well(seg_data))

            # NB: The enumeration of branches is not necessarily consecutive
            # from SEGBRNO.

            # Now we can test if we have any ICD segments, that is the
            # case if we have any segments that have SEGBRNO higher than
            # the branch count.

            seg_data, icd_data = split_seg_icd(seg_data)

            # Branch counting must be done after ICD's are split out.
            branchcount = count_wellbranches(seg_data)

            logger.info(
                "Found %d branch(es), and %d icd segment(s)", branchcount, len(icd_data)
            )

        con_icd_seg = merge_icd_seg_conseg(con_data, seg_data, icd_data)

        con_icd_seg = add_extras(con_icd_seg, inplace=True)

        con_icd_seg["DATE"] = rftrecord["date"]
        con_icd_seg["WELL"] = rftrecord["wellname"]
        con_icd_seg["WELLMODEL"] = rftrecord["wellmodel"]

        # Delete topology columns
        delete_cols = {col for col in con_icd_seg.columns if col.endswith("stream")}
        delete_cols = delete_cols.union(
            {
                "LEAF",
                "ICD_LEAF",
                "JUNCTION",
                "ICD_JUNCTION",
                "LONELYSEG",
                "ICD_LONELYSEG",
            }
        )
        con_icd_seg = con_icd_seg[set(con_icd_seg.columns) - delete_cols]

        rftdata.append(con_icd_seg)

    rftdata_df = pd.concat(rftdata, ignore_index=True, sort=False)

    # Fill empty cells with zeros. This is to avoid Spotfire
    # interpreting columns with numbers as strings. An alternative
    # solution that keeps NaN would be to add a second row in the
    # output containing the datatype
    rftdata_df.fillna(0, inplace=True)

    # The HOSTGRID data seems often to be empty, check if it is and delete if so:
    if "HOSTGRID" in rftdata_df.columns:
        if len(rftdata_df.HOSTGRID.unique()) == 1:
            if rftdata_df.HOSTGRID.unique()[0].strip() == "":
                del rftdata_df["HOSTGRID"]

    zonemap = eclfiles.get_zonemap()
    if zonemap:
        if "K" in rftdata_df:
            kname = "K"
        else:
            kname = "CONKPOS"
        rftdata_df = merge_zones(rftdata_df, zonemap, kname=kname)

    return rftdata_df


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE",
        help=(
            "Name of Eclipse DATA file or RFT file. "
            "If DATA file is provided, it will look for"
            " the associated DATA file"
        ),
    )
    parser.add_argument(
        "--wellname", type=str, help="Restrict data to one named well", default=None
    )

    parser.add_argument(
        "--date", type=str, help="Restrict data to one date, YYYY-MM-DD", default=None
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Name of output CSV file.", default="rft.csv"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    return parser


def rft_main(args) -> None:
    """Entry-point for module, for command line utility"""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    if args.DATAFILE.endswith(".RFT"):
        # Support the RFT file as an argument also:
        eclfiles = EclFiles(args.DATAFILE.replace(".RFT", "") + ".DATA")
    else:
        eclfiles = EclFiles(args.DATAFILE)
    rft_df = df(eclfiles, wellname=args.wellname, date=args.date)
    if rft_df.empty:
        if args.wellname is not None or args.date is not None:
            logger.warning("No data. Check your well and/or date filter")
        else:
            logger.error("No data found. Bug?")
        return
    write_dframe_stdout_file(rft_df, args.output, index=False, caller_logger=logger)


# Vector  Description
# CONIDX   Index of the connection pr well, starting at 1.
# CONDEPTH Depth at the centre of each connection in the well
# CONLENST Length down the tubing from the BH reference
#          point to the start of the connection
# CONLENEN Length down the tubing from the BH reference point to the
#          far end of the connection
# CONPRES  Pressure in the wellbore at the connection
# CONORAT  Oil production rate of the connection at surface conditions
# CONWRAT  Water production rate of the connection at surface conditions
# CONGRAT  Gas production rate of the connection at surface conditions
# CONOTUB  Oil flow rate through the tubing at the start of the
#          connection at surface conditions
# CONWTUB  Water flow rate through the tubing at the start of the
#          connection at surface conditions
# CONGTUB  Gas flow rate through the tubing at the start of the
#          connection at surface conditions
# CONVTUB  Volumetric flow rate of the mixture at the start of the connection
# CONFAC   Connection transmissibility factor
# CONKH    Connection Kh value
# CONNXT   Number of the neighbouring connection towards the wellhead
# CONSEGNO Segment number containing the connection
# CONBRNO  Branch number containing the connection
# CONIPOS  I location of the connection
# CONJPOS  J location of the connection
# CONKPOS  K location of the connection
# CONBDEPH Depth of the grid block of the connection
# CONBPRES Pressure of the grid block of the connection
#          (Copy of the PRESSURE data)
# CONBSWAT Water saturation of the grid block of the connection
# CONBSGAS Gas saturation of the grid block of the connection
# CONBSOIL Oil saturation of the grid block of the connection
# COMPLETION Completion index of the connection
#
# The above values are taken from the corresponding RFT data.
#
# Vector   Description
# CONMD    Measured depth of the connection
# CONLENTH Length of the connection
# CONORATS Scaled oil production rate at surface conditions
# CONWRATS Scaled water production rate at surface conditions
# CONGRATS Scaled gas production rate at surface conditions
#
#
# Vector   Description
# SEGDEPTH Depth at the far end of each segment
# SEGLENST Length down the tubing from the zero tubing length
#          reference point to the start of the segment
# SEGLELEN Length down the tubing from the zero tubing length
#          reference point to the far end of the segment
# SEGXCORD X-coordinate at the far end of the segment
#          (as entered by the 11th item of the WELSEGS record)
# SEGXCORD Y-coordinate at the far end of the segment
#          (as entered by the 12th item of the WELSEGS record)
# SEGPRES Pressure in the wellbore at the far end of the segment
# SEGORAT Oil flow rate through the segment through its near end
# SEGWRAT Water flow rate through the segment through its near end
# SEGGRAT Gas flow rate through the segment through its near end
# SEGOVEL Free oil phase velocity through the segment
# SEGWVEL Water flow velocity through the segment
# SEGGVEL Free gas phase flow velocity through the segment
# SEGOHF  Free oil phase holdup fraction in the segment
# SEGWHF  Water holdup fraction in the segment
# SEGGHF  Free gas phase holdup fraction in the segment
# SEGBRNO Branch number of the segment
# SEGNXT  Number of the neighbouring segment towards the wellhead
#
# Vector         Description
# SEGMD          Segment measured depth
# SEGLENTH       Segment length
# SEGORATSScaled water flow rate through the segment
# SEGWRATSScaled water flow rate through the segment
# SEGGRATSScaled gas flow rate through the segment
# SEGCORATSummed connection oil flow rate through segment
# SEGCWRATSummed connection water flow rate through segment
# SEGCGRATSummer connection gas flow rate through segment
# SEGCORTSScaled summed connection oil flow rate through segment
# SEGCWRTSScaled summed connection water flow rate through segment
# SEGCGRTSScaled summed connection gas flow rate through segment
