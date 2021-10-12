"""Extract statistics pr cornerpoint pillar (i,j)-pair"""

import argparse
import datetime
import logging
from typing import Dict, List, Optional, Union

import dateutil.parser
import pandas as pd

from ecl2df import EclFiles, common, getLogger_ecl2csv, grid

logger: logging.Logger = logging.getLogger(__name__)

AGGREGATORS: Dict[str, str] = {
    "VOLUME": "sum",
    "PORV": "sum",
    "PERMX": "mean",
    "PERMY": "mean",
    "PERMZ": "mean",
    "X": "mean",
    "Y": "mean",
    "Z": "mean",
    "WATVOL": "sum",
    "GASVOL": "sum",
    "OILVOL": "sum",
    "GASVOLSURF": "sum",
    "OILVOLSURF": "sum",
    "OWC": "mean",
    "GOC": "mean",
    "GWC": "mean",
}


def df(
    eclfiles: EclFiles,
    region: str = None,
    rstdates: Optional[Union[str, datetime.date, List[datetime.date]]] = None,
    soilcutoff: float = 0.2,
    sgascutoff: float = 0.7,
    swatcutoff: float = 0.7,
    stackdates: bool = False,
) -> pd.DataFrame:
    """Produce a dataframe with pillar information

    This is the "main" function for Python API users
    Produces a dataframe with data for each I-J combination
    (in the column PILLAR), and if a region parameter is
    supplied, also pr. region.

    PORV is the summed porevolume of the pillar (in the region),
    VOLUME is bulk volume, and PORO is porevolume weighted porosity
    PERM columns contain unweighted value averages, use with caution.

    If a restart date is picked, then SWAT and SGAS will
    be used to compute volumes pr. phase, WATVOL, OILVOL and GASVOL. The
    columns with dynamic data will include the date in the column headers
    like SWAT@2009-01-01

    Args:
        region: A parameter the pillars will be split
            on. Typically EQLNUM or FIPNUM. Set to empty string
            or None to avoid any region grouping.
        rstdates: Dates for which restart data
            is to be extracted. The string can
            be in ISO-format, or one of the mnenomics
            'first', 'last' or 'all'. It can also be a list
            of datetime.date.
        soilcutoff: If not None, an oil-water contact will
            be estimated pr. pillar, based on the deepest cell with
            SOIL above the given cutoff. Value is put in column OWC.
        sgascuttof: If not None, a gas contact will be
            estimated pr pillar, based on the deepest cell with
            SGAS above the given cutoff. Value is put in column GOC.
        swatcutoff: OWC or GWC is only computed for pillars
            where at least one cell is above this value.
        stackdates: If true, a column
            called DATE will be added and data for all restart
            dates will be added in a stacked manner.
    """
    # List of vectors we want, conservative in order to save memory and cputime:
    vectors = []
    if region:
        vectors.append(region)
    vectors.extend(["POR*", "PERM*", "SWAT", "SGAS", "1OVERBO", "1OVERBG"])
    grid_df = grid.df(eclfiles, rstdates=rstdates, vectors=vectors, dateinheaders=True)

    rstdates_iso = grid.dates2rstindices(eclfiles, rstdates)[2]

    grid_df["PILLAR"] = grid_df["I"].astype(str) + "-" + grid_df["J"].astype(str)
    logger.info("Computing pillar statistics")
    groupbies = ["PILLAR"]
    if region:
        if region not in grid_df:
            logger.warning("Region parameter %s not found, ignored", region)
        else:
            groupbies.append(region)
            grid_df[region] = grid_df[region].astype(int)

    for datestr in rstdates_iso:
        logger.info("Dynamic volumes for %s", datestr)
        volumes = compute_volumes(grid_df, datestr=datestr)
        grid_df = pd.concat([grid_df, volumes], axis="columns", sort=False)

    aggregators = {
        key: AGGREGATORS[key.split("@")[0]]
        for key in grid_df
        if key.split("@")[0] in AGGREGATORS
    }

    # Group over PILLAR and possibly regions:
    grouped = (grid_df.groupby(groupbies).agg(aggregators)).reset_index()

    # Compute correct pillar averaged porosity (from bulk)
    if "PORV" in grouped and "VOLUME" in grouped:
        grouped["PORO"] = grouped["PORV"] / grouped["VOLUME"]

    # Compute contacts:
    for datestr in rstdates_iso:
        if "SWAT@" + datestr in grid_df and (
            "SOIL@" + datestr in grid_df or "SGAS@" + datestr in grid_df
        ):
            contacts = compute_pillar_contacts(
                grid_df,
                region=region,
                soilcutoff=soilcutoff,
                sgascutoff=sgascutoff,
                swatcutoff=swatcutoff,
                datestr=datestr,
            )
            if not contacts.empty:
                grouped = pd.merge(grouped, contacts, how="left")

    if stackdates:
        return common.stack_on_colnames(
            grouped, sep="@", stackcolname="DATE", inplace=True
        )
    return grouped


def compute_volumes(
    grid_df: pd.DataFrame, datestr: Optional[str] = None
) -> pd.DataFrame:
    """Compute "dynamic" volumes, volumes for data coming from the
    UNRST file (SWAT+SGAS)

    SOIL is assumed not be present in grid_df, it will be computed here.

    Args:
        grid_df: A dataframe with the columns PORV, SWAT and SGAS
        datestr: If not none, it should contain an ISO-8601 formatted date that
            will be appended to all columns with dynamic data, SWAT and SGAS
            in incoming grid_df must also be appended with the same date string.
            If datestr is "2009-01-02", then the columns will look
            like "SOIL@2009-01-02"
    """
    if datestr:
        assert isinstance(dateutil.parser.parse(datestr).date(), datetime.date)
        atdatestr = "@" + str(datestr)
    else:
        atdatestr = ""
    vols = pd.DataFrame()
    if "SWAT" + atdatestr in grid_df and "SGAS" + atdatestr in grid_df:
        vols["SOIL" + atdatestr] = (
            1 - grid_df["SWAT" + atdatestr] - grid_df["SGAS" + atdatestr]
        )
    if "SWAT" + atdatestr in grid_df and "SGAS" + atdatestr not in grid_df:
        # Two-phase oil-water
        vols["SOIL" + atdatestr] = 1 - grid_df["SWAT" + atdatestr]
        # (or it could be two-phase water-gas, but then the SOIL would mean the same)

    if "SWAT" + atdatestr in grid_df:
        vols["WATVOL" + atdatestr] = grid_df["SWAT" + atdatestr] * grid_df["PORV"]
    if "SGAS" + atdatestr in grid_df:
        vols["GASVOL" + atdatestr] = grid_df["SGAS" + atdatestr] * grid_df["PORV"]
    if "SOIL" + atdatestr in vols:
        vols["OILVOL" + atdatestr] = vols["SOIL" + atdatestr] * grid_df["PORV"]

    if "1OVERBO" + atdatestr in grid_df and "OILVOL" + atdatestr in vols:
        vols["OILVOLSURF" + atdatestr] = (
            vols["OILVOL" + atdatestr] * grid_df["1OVERBO" + atdatestr]
        )

    if "1OVERBG" + atdatestr in grid_df and "GASVOL" + atdatestr in vols:
        vols["GASVOLSURF" + atdatestr] = (
            vols["GASVOL" + atdatestr] * grid_df["1OVERBG" + atdatestr]
        )
    return vols


def compute_pillar_contacts(
    grid_df: pd.DataFrame,
    region: Optional[str] = None,
    soilcutoff: float = 0.2,
    sgascutoff: float = 0.7,
    swatcutoff: float = 0.7,
    datestr: Optional[str] = None,
) -> pd.DataFrame:
    """Compute contacts pr. pillar in a grid dataframe.

    Requires the columns PILLAR, SOIL, SGAS and SWAT, I, J and Z

    SOIL should be pre-computed in three-phase runs before calling this.
    PILLAR must be pre-computed in grid_df.

    OWC is deepest cell centre pr. pillar with oil saturation above soilcutoff,
    among those pillars with at least one cell above swatcutoff.

    GOC is the deepest cell centre pr. pillar with gas saturation above sgascutoff,
    among those pillars with at least one cell with non-zero oil saturation

    GWC is only computed when SOIL is not presented, and is the deepest
    cell centre with gas saturation above sgascutoff, among those pillars
    with at least one cell above swatcutoff.

    Args:
        grid_df: Representing the grid with geometry and properties
        region: Region vector to group by, e.g. FIPNUM or EQLNUM
        soilcutoff: OWC is deepest cell centre pr. pillar with oil
            saturation above this
        sgascutoff: GOC/GWC is deepest cell centre pr. pillar with
            gas saturation above this
        swatcutoff: Pillars must have this amount of water in (in one cell)
            them to be available for OWC/GWC computations.
    Returns:
        Index is PILLAR with values I-J. Rows only for
        pillars where a contact was found. Empty dataframe if no contacts found.
    """
    assert 0 <= swatcutoff <= 1
    assert 0 <= soilcutoff <= 1
    assert 0 <= sgascutoff <= 1

    # assert datestr is None or in ISO-8601 format
    if datestr:
        atdatestr = "@" + datestr
    else:
        atdatestr = ""

    # Non-user servicable parameter, for GOC computation
    # we require cells at the contact to contain a minute saturation
    # of oil. This is to avoid the code picking up gas injected in the
    # water phase.
    epsilon_soil = 0.01

    if "SWAT" + atdatestr not in grid_df:
        logger.warning("No saturation in grid data. No contacts computed")
        return pd.DataFrame()
    logger.info("Computing contacts pr. pillar")
    groupbies = ["PILLAR"]
    if "PILLAR" not in grid_df:
        grid_df["PILLAR"] = grid_df["I"].astype(str) + "-" + grid_df["J"].astype(str)

    if "Z" not in grid_df:
        # To ensure same exception across Python 3.x:
        raise KeyError("Z column must be present in dataframe")

    if region:
        groupbies.append(region)
    owc = pd.DataFrame()
    goc = pd.DataFrame()

    # Extract pillars with water in them. Only here would an OWC make sense.
    waterpillars = (
        grid_df[grid_df["SWAT" + atdatestr] > swatcutoff]
        .groupby(groupbies)
        .agg({"Z": "min"})
        .reset_index()
    )
    if soilcutoff and "SOIL" + atdatestr in grid_df:
        logger.info(
            "Calculating oil-water-contacts based on SOILcutoff %s", str(soilcutoff)
        )
        owc = (
            grid_df[grid_df["SOIL" + atdatestr] > soilcutoff]
            .groupby(groupbies)
            .agg({"Z": "max"})
        )
        owc.rename(columns={"Z": "OWC" + atdatestr}, inplace=True)
        owc.reset_index(inplace=True)
        # Filter the owc frame to only those pillars that also has water:
        owc = pd.merge(waterpillars, owc, how="inner").drop("Z", axis="columns")

    if sgascutoff and "SGAS" + atdatestr in grid_df:
        logger.info("Calculating gas-contacts based on gas cutoff %s", str(sgascutoff))
        if "SOIL" + atdatestr in grid_df and "SGAS" + atdatestr in grid_df:
            # Pillars to be used for GOC computation
            gocpillars = (
                grid_df[grid_df["SOIL" + atdatestr] > epsilon_soil]
                .groupby(groupbies)
                .agg({"Z": "first"})  # The actual aggregation is not used.
                .reset_index()
            )
            goc = (
                grid_df[
                    (grid_df["SGAS" + atdatestr] > sgascutoff)
                    & (grid_df["SOIL" + atdatestr] > epsilon_soil)
                ]
                .groupby(groupbies)
                .agg({"Z": "max"})
            )
            goc.rename(columns={"Z": "GOC" + atdatestr}, inplace=True)
        else:
            # Two-phase gas-water: GWC computation
            gocpillars = waterpillars  # In case of gas-water
            goc = (
                grid_df[grid_df["SGAS" + atdatestr] > sgascutoff]
                .groupby(groupbies)
                .agg({"Z": "max"})
            )
            goc.rename(columns={"Z": "GWC" + atdatestr}, inplace=True)
        goc.reset_index(inplace=True)
        # Filter the goc frame to only those with oil or water:
        goc = pd.merge(gocpillars, goc, how="inner").drop("Z", axis="columns")

    # We need to avoid merging with potentially empty DataFrames
    if owc.empty and goc.empty:
        return pd.DataFrame()
    if not owc.empty and goc.empty:
        return owc
    if owc.empty and not goc.empty:
        return goc
    return pd.merge(owc, goc)


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parser.

    Arguments:
        parser: argparse.ArgumentParser or argparse.subparser
    """
    parser.add_argument(
        "DATAFILE",
        help=("Name of Eclipse DATA file. " "INIT and EGRID file must lie alongside."),
    )
    parser.add_argument(
        "--region",
        help=(
            "Name of Eclipse region parameter for which to separate the computations. "
            "Set to empty string to have no grouping (only by pillar)."
        ),
        type=str,
        default="",
    )
    parser.add_argument(
        "--rstdates",
        type=str,
        help=(
            "Point in time to grab restart data from, "
            "either 'first' or 'last', 'all' or a date in "
            "YYYY-MM-DD format"
        ),
        default="",
    )
    parser.add_argument(
        "--stackdates",
        action="store_true",
        help=(
            "If set, the dates from restart data will not be in the column "
            "but instead there will be a DATE column with the dates. Note "
            "that the static data will be repeated for each DATE."
        ),
    )
    parser.add_argument(
        "--soilcutoff",
        type=float,
        help=(
            "If supplied as float, an oil-water contact will "
            "be estimated pr. pillar, based on the deepest cell with "
            "SOIL above the given cutoff. Value is put in column OWC."
        ),
        default=0.5,
    )
    parser.add_argument(
        "--sgascutoff",
        type=float,
        help=(
            "If supplied, a gas contact will be "
            "estimated pr pillar, based on the deepest cell with "
            "SGAS above the given cutoff. Value is put in column GOC. "
        ),
        default=0.5,
    )
    parser.add_argument(
        "--swatcutoff",
        type=float,
        help=(
            "For OWC or GWC computations, only pillars with at least one cell "
            "with water saturation above this value will be considered."
        ),
        default=0.5,
    )
    parser.add_argument(
        "--group",
        action="store_true",
        help=(
            "If set, output will not be pr. pillar, but grouped over "
            "all pillars. If --region is set, data will be grouped over that vector. "
            "The aggregation operator is sum or mean, depending on datatype."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file.",
        default="pillars.csv",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def pillars_main(args) -> None:
    """This is the command line API"""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )

    eclfiles = EclFiles(args.DATAFILE)
    dframe = df(
        eclfiles,
        region=args.region,
        rstdates=args.rstdates,
        soilcutoff=args.soilcutoff,
        sgascutoff=args.sgascutoff,
        swatcutoff=args.swatcutoff,
        stackdates=args.stackdates,
    )
    groupbies = []
    aggregators = {
        key: AGGREGATORS[key.split("@")[0]]
        for key in dframe
        if key.split("@")[0] in AGGREGATORS
    }
    if args.region and args.group:
        groupbies.append(args.region)
    if args.stackdates and args.group:
        groupbies.append("DATE")
    if groupbies:
        dframe = dframe.groupby(groupbies).agg(aggregators).reset_index()
    elif args.group:
        dframe = dframe.drop("PILLAR", axis=1).mean().to_frame().transpose()
    dframe["PORO"] = dframe["PORV"] / dframe["VOLUME"]
    common.write_dframe_stdout_file(
        dframe, args.output, index=False, caller_logger=logger
    )
