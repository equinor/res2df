from typing import Optional
from dataclasses import dataclass  # (backport for 3.6)
import logging

import pandas as pd

from ecl.summary import EclSum
from ecl.util.util import CTime

logger = logging.getLogger("ecl2df.summary")


@dataclass
class EclipseVectorDefinition:
    raw_key: str
    full_key: str
    main_key: str
    unit: str
    num: Optional[int] = 0
    well_or_group_key: Optional[str] = None


def _get_ecl_key(column: str, unit_system: str = "METRIC"):
    """Return a list of eclipse str keys for use in EclSum.addVariable

    The names/columns may be in the formats::

      FOPR
      GOPR:grpname or WOPR:wellname and so forth
      BPR:13,2,3

    """
    if not unit_system == "METRIC":
        raise ValueError(f'Unit system {unit_system} not supported, use "METRIC".')

    main_key, _, sub_key = column.partition(":")

    well_or_group = None
    sub_key_as_number = 0

    if sub_key is not None:
        try:
            sub_key_as_number = int(sub_key)
        except ValueError:
            well_or_group = sub_key

    if EclSum.is_rate(main_key):
        unit = "Sm3/day"
    elif EclSum.is_total(main_key):
        unit = "Sm3"
    else:
        logger.debug("Unit not recognized for %s", column)
        unit = "foooSm3"
        # unit = None

    return EclipseVectorDefinition(
        raw_key=column,
        full_key=column,
        main_key=main_key,
        well_or_group_key=well_or_group,
        unit=unit,
        num=sub_key_as_number,
    )


SECONDS_PER_DAY = 86400.0


def _time_delta_to_days(timedelta: pd.Timedelta) -> float:
    return timedelta.total_seconds() / SECONDS_PER_DAY


def df2eclsum(
    dframe: pd.DataFrame,
    case_name: str,
):
    """Convert a dataframe to an EclSum object

    Args:
        dframe (pd.DataFrame): Dataframe with a DATE colum (or with the
            dates/datetimes in the index).
        case_name: Name of Eclipse basename to be used for the EclSum object
            If the EclSum object is later written to disk, this will be used
            to construct the filenames.

    Returns:
        EclSum
    """

    if "DATE" in dframe.columns:
        dframe.set_index("DATE", inplace=True, drop=True)
    dframe = dframe.sort_index(axis=0)
    dates = dframe.index
    days_from_start = [_time_delta_to_days(timestep - dates[0]) for timestep in dates]
    dates_ctime = [CTime(date) for date in dframe.index]

    dummy_grid_resolution = (1, 1, 1)
    eclsum = EclSum.restart_writer(
        case=case_name,
        restart_case=None,
        restart_step=-1,
        start_time=dates_ctime[0],
        nx=dummy_grid_resolution[0],
        ny=dummy_grid_resolution[1],
        nz=dummy_grid_resolution[2],
    )
    columns = dframe.columns.values

    # BPR does not work (yet), filter out:
    columns = [col for col in columns if "BPR" not in col]

    vectors = [_get_ecl_key(column=column) for column in columns]
    for vector in vectors:
        eclsum.add_variable(
            variable=vector.main_key,
            wgname=vector.well_or_group_key,
            num=vector.num,
            unit=vector.unit,
        )

    for report_step, date in enumerate(dates):
        tstep = eclsum.add_t_step(
            report_step=report_step, sim_days=days_from_start[report_step]
        )
        for vector in vectors:
            tstep[vector.full_key] = dframe.get(vector.raw_key)[report_step]

    return eclsum


def fill_reverse_parser(parser):
    """Fill a parser for the operation:  dataframe -> eclsum files"""
    parser.add_argument("csvfile", help="Name of CSV file with summary data.")
    parser.add_argument("ECLBASE", help="Basename for Eclipse output files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument("--debug", action="store_true", help="Be verbose")
    return parser


def summary_reverse_main(args):
    """Entry point for usage with "csv2ecl summary" on the command line"""
    if args.verbose and not args.debug:
        logging.basicConfig(level=logging.INFO)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    summary_df = pd.read_csv(args.csvfile, parse_dates=["DATE"])
    logger.info("Parsed %s", args.csvfile)

    eclsum = df2eclsum(summary_df, args.ECLBASE)
    EclSum.fwrite(eclsum)
    logger.info(
        "Wrote to %s and %s", args.ECLBASE + ".UNSMRY", args.ECLBASE + ".SMSPEC"
    )
