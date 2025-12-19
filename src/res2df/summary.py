"""Provide a two-way Pandas DataFrame interface to Eclipse summary data (UNSMRY)"""

import argparse

# The name 'datetime' is in use by a function argument:
import datetime as dt
import logging
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import dateutil
import numpy as np
import pandas as pd
import pyarrow as pa
from resdata.summary import Summary

from .common import write_dframe_stdout_file
from .parameters import find_parameter_files, load, load_all
from .res2csvlogger import getLogger_res2csv
from .resdatafiles import ResdataFiles

logger: logging.Logger = logging.getLogger(__name__)

# Frequency mnemonics for the API consumer to use:
FREQ_RAW: str = "raw"
FREQ_FIRST: str = "first"
FREQ_LAST: str = "last"
PD_FREQ_MNEMONICS: dict[str, str] = {
    "daily": "D",
    "weekly": "W-MON",
    "monthly": "MS",
    "yearly": "YS",
    # Any frequency mnemonics not mentioned here will be
    # passed on to Pandas.
}
"""Mapping from res2df custom offset strings to Pandas DateOffset strings.
See
https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#dateoffset-objects
"""


def date_range(
    start_date: dt.date, end_date: dt.date, freq: str
) -> Iterable[dt.datetime]:
    """Wrapper for pandas.date_range to allow for extra res2df specific mnemonics
    'yearly', 'daily', 'weekly', mapped over to pandas DateOffsets.

    Args:
        start_date (datetime.date):
        end_date (datetime.date):
        freq (str): monthly, daily, weekly, yearly, or a Pandas date offset
            frequency.

    Returns:
        list of datetimes
    """
    try:
        return pd.date_range(
            start_date, end_date, freq=PD_FREQ_MNEMONICS.get(freq, freq)
        )
    except pd.errors.OutOfBoundsDatetime:
        return _fallback_date_range(start_date, end_date, freq)


def _ensure_date_or_none(some_date: str | dt.date | None) -> dt.date | None:
    """Ensures an object is either a date or None

    Args:
        some_date: string or a datetime.date

    Returns:
        None if input is None.
    """
    if some_date is None:
        return None
    if isinstance(some_date, dt.date):
        return some_date
    if not some_date:
        return None
    if isinstance(some_date, str):
        return dateutil.parser.parse(some_date).date()
    raise TypeError(f"some_date must be a string or a date, got {some_date}")


def _crop_datelist(
    summarydates: list[dt.datetime],
    freq: dt.date | dt.datetime | str,
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
) -> list[dt.date] | list[dt.datetime]:
    """Helper function for resample_smry_dates, taking care of
    the special cases where the list of dates should not be resampled, but
    only cropped or returned as is.

    Args:
        summarydates: list of datetimes, typically coming from Summary.dates
        freq: Either a date or datetime, or a frequency string
            "raw", "first" or "last".
        start_date: Dates prior to this date will be cropped.
        end_date: Dates after this date will be cropped.

    Returns:
        list of datetimes.
    """
    datetimes: list[dt.date] | list[dt.datetime] = []
    if freq == FREQ_RAW:
        datetimes = summarydates
        datetimes.sort()
        if start_date:
            # Convert to datetime (at 00:00:00)
            start_date = dt.datetime.combine(start_date, dt.datetime.min.time())
            datetimes = [x for x in datetimes if x > start_date]
            datetimes = [start_date, *datetimes]
        if end_date:
            end_date = dt.datetime.combine(end_date, dt.datetime.min.time())
            datetimes = [x for x in datetimes if x < end_date]
            datetimes += [end_date]
    elif freq == FREQ_FIRST:
        datetimes = [min(summarydates).date()]
    elif freq == FREQ_LAST:
        datetimes = [max(summarydates).date()]
    elif isinstance(freq, (dt.date, dt.datetime)):
        datetimes = [freq]
    return datetimes


def _fallback_date_roll(rollme: dt.datetime, direction: str, freq: str) -> dt.datetime:
    """Fallback function for rolling dates forward or backward onto a
    date frequency boundary.

    This function reimplements pandas' DateOffset.roll_forward() and backward()
    only for monthly and yearly frequency. This is necessary as Pandas does not
    support datetimes beyond year 2262 due to all datetimes in Pandas being
    represented by nanosecond accuracy.

    This function is a fallback only, to keep support for using all Pandas timeoffsets
    in situations where years beyond 2262 is not a issue."""
    if direction not in ["back", "forward"]:
        raise ValueError(f"Unknown direction {direction}")

    if freq == "yearly":
        if direction == "forward":
            if rollme <= dt.datetime(year=rollme.year, month=1, day=1):
                return dt.datetime(year=rollme.year, month=1, day=1)
            return dt.datetime(year=rollme.year + 1, month=1, day=1)
        return dt.datetime(year=rollme.year, month=1, day=1)

    if freq == "monthly":
        if direction == "forward":
            if rollme <= dt.datetime(year=rollme.year, month=rollme.month, day=1):
                return dt.datetime(year=rollme.year, month=rollme.month, day=1)
            return dt.datetime(
                year=rollme.year, month=rollme.month, day=1
            ) + dateutil.relativedelta.relativedelta(months=1)
        return dt.datetime(year=rollme.year, month=rollme.month, day=1)

    raise ValueError(
        "Only yearly or monthly frequencies are "
        "supported for simulations beyond year 2262"
    )


def _fallback_date_range(start: dt.date, end: dt.date, freq: str) -> list[dt.datetime]:
    """Fallback routine for generating date ranges beyond Pandas datetime64[ns]
    year-2262 limit.

    Assumes that the start and end times already fall on a frequency boundary.
    """
    if start == end:
        return [dt.datetime.combine(start, dt.datetime.min.time())]
    if end < start:
        return []
    if freq == "yearly":
        dates = [dt.datetime.combine(start, dt.datetime.min.time())] + [
            dt.datetime(year=year, month=1, day=1)
            for year in range(start.year + 1, end.year + 1)
        ]
        if dt.datetime.combine(end, dt.datetime.min.time()) != dates[-1]:
            dates += [dt.datetime.combine(end, dt.datetime.min.time())]
        return dates
    if freq == "monthly":
        dates = []
        date = dt.datetime.combine(start, dt.datetime.min.time())
        enddatetime = dt.datetime.combine(end, dt.datetime.min.time())
        while date <= enddatetime:
            dates.append(date)
            date += dateutil.relativedelta.relativedelta(months=1)
        return dates
    raise ValueError("Unsupported frequency for datetimes beyond year 2262")


def resample_smry_dates(
    summarydates: list[dt.datetime],
    freq: str = FREQ_RAW,
    normalize: bool = True,
    start_date: str | dt.date | None = None,
    end_date: str | dt.date | None = None,
) -> list[dt.date] | list[dt.datetime]:
    """
    Resample (optionally) a list of date(time)s to a new datelist according to options.

    Based on the dates as input, a new list at a finer or coarser time density
    can be returned, on the same date range. Incoming dates can also be cropped.

    Args:
        summarydates: list of datetimes, typically coming from Summary.dates
        freq: string denoting requested frequency for
            the returned list of datetime. 'raw' will
            return the input datetimes (no resampling).
            Options for timeresampling are
            'daily', 'weekly', 'monthly' and 'yearly'. 'first' will give
            the first date (minimum),  'last' will give out the last
            date (maximum), as a list with one element. Can also be a single date.
        normalize: Whether to normalize backwards at the start
            and forwards at the end to ensure the raw
            date range is covered when resampling time. This is
            ignored if start_date or end_date is explicitly supplied.
        start_date: str or date with first date to include
            Dates prior to this date will be dropped, supplied
            start_date will always be included. Overrides
            normalized dates.
        end_date: str or date with last date to be included.
            Dates past this date will be dropped, supplied
            end_date will always be included. Overrides
            normalized dates. Overridden if freq is 'last'.
    """
    start_date = _ensure_date_or_none(start_date)
    end_date = _ensure_date_or_none(end_date)

    if freq in [FREQ_RAW, FREQ_FIRST, FREQ_LAST] or isinstance(
        freq, (dt.date, dt.datetime)
    ):
        return _crop_datelist(summarydates, freq, start_date, end_date)

    # In case freq is an ISO-date(time)-string, interpret as such:
    try:
        parseddate = dateutil.parser.isoparse(freq)
        return [parseddate]
    except ValueError:
        # freq is a frequency string or datetime.date (or similar)
        pass

    # These are datetime.datetime, not datetime.date
    start_smry = min(summarydates)
    end_smry = max(summarydates)

    # Normalize start and end date according to frequency by extending the time range.
    # [1997-11-05, 2020-03-02] and monthly frequecy
    # will be mapped to [1997-11-01, 2020-04-01]
    # For yearly frequency it will return [1997-01-01, 2021-01-01].
    offset = pd.tseries.frequencies.to_offset(PD_FREQ_MNEMONICS.get(freq, freq))
    try:
        start_normalized = offset.rollback(start_smry).date()
    except pd.errors.OutOfBoundsDatetime:
        # Pandas only supports datetime up to year 2262
        start_normalized = _fallback_date_roll(start_smry, "back", freq).date()
    try:
        end_normalized = offset.rollforward(end_smry).date()
    except pd.errors.OutOfBoundsDatetime:
        # Pandas only supports datetime up to year 2262
        end_normalized = _fallback_date_roll(end_smry, "forward", freq).date()

    if start_date is None:
        start_date_range = start_normalized if normalize else start_smry.date()
    else:
        # Normalization is not applied for explicit date
        start_date_range = start_date

    if end_date is None:
        end_date_range = end_normalized if normalize else end_smry.date()
    else:
        # Normalization is not applied for explicit date
        end_date_range = end_date

    datetimes = date_range(start_date_range, end_date_range, freq)

    # Convert from numpys datetime64 to datetime.date:
    dates = [x.date() for x in datetimes]

    # pd.date_range will not include random dates that do not
    # fit on frequency boundary. Force include these if
    # supplied as user arguments.
    if start_date and start_date not in dates:
        dates = [start_date, *dates]
    if end_date and end_date not in dates:
        dates += [end_date]
    return dates


def df(
    resdatafiles: ResdataFiles,
    time_index: str | None = None,
    column_keys: list[str] | str | None = None,
    start_date: str | dt.date | None = None,
    end_date: str | dt.date | None = None,
    include_restart: bool = False,
    params: bool = False,
    paramfile: str | None = None,
    datetime: bool = False,  # A very poor choice of argument name [pylint]
) -> pd.DataFrame:
    """
    Extract data from UNSMRY as Pandas dataframes.

    This is a thin wrapper for Summary.pandas_frame, by adding
    support for string mnenomics for the time index.

    The dataframe is always indexed by DATE, and the datatype for the
    index will usually be datetime64[ns] as long as all dates are
    before year 2262. If a longer time range is detected, the index.dtype
    will be object, and consisting of datetime.datetime() objects. The index
    is always named "DATE".

    Arguments:
        resdatafiles: ResdataFiles object representing a
            :term:`.DATA file`. Alternatively a Summary object.
        time_index: string indicating a resampling frequency,
           'yearly', 'monthly', 'daily', 'last' or 'raw', the latter will
           return the simulated report steps (also default).
           If a list of DateTime is supplied, data will be resampled
           to these.
        column_keys: list of column key wildcards. None means everything.
        start_date: str or date with first date to include.
            Dates prior to this date will be dropped, supplied
            start_date will always be included.
        end_date: str or date with last date to be included.
            Dates past this date will be dropped, supplied
            end_date will always be included. Overriden if time_index
            is 'last'.
        include_restart: boolean sent to resdata for whether restart
            files should be traversed
        params: If set, parameters.txt will be attempted loaded
            and merged with the summary data.
        paramsfile: Explicit path to parameters file if autodiscovery is
            not wanted. Implies params=True
        datetime: If True, the time index of the returned DataFrame
            is always of datetime type. If not, it will be datetime
            if raw dates are requested (which are at second accuracy),
            or it will be strings in case of yearly, monthly or daily
            time frequency.

    Returns empty dataframe if there is no summary file, or if the
    column_keys are not existing.
    """
    if isinstance(column_keys, str):
        column_keys = [column_keys]

    if isinstance(resdatafiles, Summary):
        summary = resdatafiles
    else:
        try:
            summary = resdatafiles.get_summary(include_restart=include_restart)
        except OSError:
            logger.warning("Error reading summary instance, returning empty dataframe")
            return pd.DataFrame()

    time_index_arg: list[dt.date] | list[dt.datetime] | None
    if isinstance(time_index, str) and time_index == "raw":
        time_index_arg = resample_smry_dates(
            summary.dates,
            "raw",
            False,
            start_date,
            end_date,
        )
    elif isinstance(time_index, str):
        time_index_arg = resample_smry_dates(
            summary.dates,
            time_index,
            True,
            start_date,
            end_date,
        )
    else:
        time_index_arg = time_index

    if time_index_arg is None:
        time_index_str = ""
    if isinstance(time_index_arg, (list, np.ndarray)):
        if len(time_index_arg) < 6:
            time_index_str = str(time_index_arg)
        else:
            time_index_str = f"{time_index_arg[0:3]} … {time_index_arg[-3:]}"

    if not column_keys or not column_keys[0]:
        column_keys_str = "*"
        # column_keys = [column_keys_str]
    else:
        column_keys_str = ",".join(filter(None, column_keys))
    logger.info(
        "Requesting columns_keys: %s at time_index: %s",
        column_keys_str,
        time_index_str or "raw",
    )

    dframe = summary.pandas_frame(time_index_arg, column_keys)

    logger.info(
        "Dataframe with smry data ready, %d columns and %d rows",
        len(dframe.columns),
        len(dframe),
    )
    dframe.index.name = "DATE"
    if params or paramfile:
        dframe = _merge_params(dframe, paramfile, resdatafiles)

    # Add metadata as an attribute the dataframe, using experimental Pandas features:
    meta = smry_meta(summary)
    # Slice meta to dataframe columns:
    dframe.attrs["meta"] = {
        column_key: meta[column_key] for column_key in dframe if column_key in meta
    }

    # Remove duplicated column names. These will occur from resdata
    # when the user has repeated vector names in the summary SECTION
    dupes = dframe.columns.duplicated()
    if dupes.any():
        logger.warning(
            "Duplicated columns detected, check your .DATA file "
            "for repeated vectors in the SUMMARY section"
        )
        logger.warning("Duplicates: %s", list(dframe.columns[dupes]))
        dframe = dframe.loc[:, ~dframe.columns.duplicated()]

    dframe = _ensure_unique_datetime_index(dframe)

    if datetime is True and dframe.index.dtype == "object":
        dframe.index = pd.to_datetime(dframe.index)

    return dframe


def _ensure_unique_datetime_index(dframe: pd.DataFrame) -> pd.DataFrame:
    """
    The TIME vector may be stored with a lower resolution than individual
    timesteps, leading ecl to return non-unique datetimes.

    Non-unique datetimes may cause troubles for the consumer. Therefore
    attempting to utilize the TIMESTEP vector to separate non-unique datetimes.

    If the optional TIMESTEP vector is not available, a ValueError is raised with a
    recommendation to rerun the simulation with the TIMESTEP vector in the SUMMARY
    section of the.
    """
    index_duplicates = dframe.index.duplicated(keep="first")
    if any(index_duplicates):
        index_duplicate_log_string = ""
        for idx in dframe.index[index_duplicates]:
            index_duplicate_log_string += f"\n{idx}"

        if "TIMESTEP" in dframe:
            logger.info(
                "Dataframe of summary data contained duplicate timestamps due to "
                "limited output resolution. Vector TIMESTEP exists, utilizing it to "
                "create discrete timestamps."
                f"Original duplicates were:{index_duplicate_log_string}"
            )
            index_as_list = dframe.index.to_list()

            if dframe.attrs["meta"]["TIMESTEP"]["unit"] == "DAYS":
                for idx in np.where(index_duplicates)[0]:
                    index_as_list[idx] += dt.timedelta(
                        days=dframe["TIMESTEP"].iloc[idx]
                    )
            elif dframe.attrs["meta"]["TIMESTEP"]["unit"] == "HOURS":
                for idx in np.where(index_duplicates)[0]:
                    index_as_list[idx] += dt.timedelta(hours=dframe["TIMESTEP"][idx])
            else:
                raise ValueError(
                    "Dataframe of smry data contained duplicate timestamps. "
                    "Vector TIMESTEP exists, but unit could not be identified."
                )
            dframe.index = pd.Series(data=index_as_list, name=dframe.index.name)
        else:
            raise ValueError(
                "Dataframe of summary data contained duplicate timestamps due to "
                "limited output resolution. Vector TIMESTEP was not found. Try to add "
                "it to the SUMMARY section of the simulation deck, as it may be "
                "utilized to separate duplicate timestamps."
            )
    return dframe


def _df2pyarrow(dframe: pd.DataFrame) -> pa.Table:
    """Construct a Pyarrow table from a dataframe, conserving metadata.

    All integer columns will have datatype int32, all floats will have float32
    as this is Eclipse specific.

    Metadata values will be written as strings. A True property is thus
    represented as the string "True" in the arrow object.

    The index in the dataframe is always assumed to be a time-index, but
    not necessarily a Pandas datetimetype (which is only of nanosecond precision).
    This index is always named DATE in the pyarrow table.
    """

    field_list: list[pa.Field] = []
    field_list.append(pa.field("DATE", pa.timestamp("ms")))
    column_arrays = [dframe.index.to_numpy().astype("datetime64[ms]")]

    dframe_values = dframe.to_numpy().transpose()
    for col_idx, colname in enumerate(dframe.columns):
        if "meta" in dframe.attrs and colname in dframe.attrs["meta"]:
            # Boolean objects in the metadata dictionary must be converted to bytes:
            field_metadata = {
                bytes(key, encoding="ascii"): bytes(str(value), encoding="ascii")
                for key, value in dframe.attrs["meta"][colname].items()
            }
        else:
            field_metadata = {}
        if pd.api.types.is_integer_dtype(dframe.dtypes[colname]):
            dtype = pa.int32()
        elif pd.api.types.is_string_dtype(dframe.dtypes[colname]):
            # Parameters are potentially merged into the dataframe.
            dtype = pa.string()
        else:
            dtype = pa.float32()
        field_list.append(pa.field(colname, dtype, metadata=field_metadata))
        column_arrays.append(dframe_values[col_idx])

    schema = pa.schema(field_list)

    return pa.table(column_arrays, schema=schema)


def _merge_params(
    dframe: pd.DataFrame,
    paramfile: str | Path | None = None,
    resdatafiles: str | ResdataFiles | None = None,
) -> pd.DataFrame:
    """Locate parameters in a <key> <value> file and add to the dataframe.

    Will fetch parameters directly from a text file if provided, or look up
    the parameters.txt file based on the location of an Eclise run.
    """

    if paramfile is None and resdatafiles is not None:
        param_files = find_parameter_files(resdatafiles)
        logger.info("Loading parameters from files: %s", param_files)
        param_dict = load_all(param_files)
    elif (
        paramfile is not None
        and resdatafiles is not None
        and not Path(paramfile).is_absolute()
    ):
        param_files = find_parameter_files(resdatafiles, filebase=str(paramfile))
        logger.info("Loading parameters from files: %s", param_files)
        param_dict = load_all(param_files)
    elif paramfile is not None and Path(paramfile).is_absolute():
        logger.info("Loading parameters from file: %s", paramfile)
        param_dict = load(paramfile)
    else:
        raise ValueError("Not able to locate parameters.txt")
    logger.info("Loaded %d parameters", len(param_dict))
    for key in param_dict:
        # By converting to str we are more robust with respect to what objects are
        # read from the parameters.json/txt/yml. Since we are only going
        # to dump to csv, it should not cause side-effects that floats end up
        # as strings in the dataframe.
        dframe[key] = str(param_dict[key])
    return dframe


def smry_meta(resdatafiles: ResdataFiles) -> dict[str, dict[str, Any]]:
    """Provide metadata for summary data vectors.

    A dictionary indexed by summary vector name is returned, and each
    value is dictionary with the metadata types provided by the underlying
    Summary object:

    * unit (string)
    * is_total (bool)
    * is_rate (bool)
    * is_historical (bool)
    * get_num (int) (only provided if not None)
    * keyword (str)
    * wgname (str or None)
    """
    if isinstance(resdatafiles, Summary):
        summary = resdatafiles
    else:
        summary = resdatafiles.get_summary()

    meta: dict[str, dict[str, Any]] = {}
    for col in summary:
        meta[col] = {}
        meta[col]["unit"] = summary.unit(col)
        meta[col]["is_total"] = summary.is_total(col)
        meta[col]["is_rate"] = summary.is_rate(col)
        meta[col]["is_historical"] = summary.smspec_node(col).is_historical()
        meta[col]["keyword"] = summary.smspec_node(col).keyword
        meta[col]["wgname"] = summary.smspec_node(col).wgname
        num = summary.smspec_node(col).get_num()
        if num is not None:
            meta[col]["get_num"] = num
    return meta


def _fix_dframe_for_resdata(dframe: pd.DataFrame) -> pd.DataFrame:
    """Fix a dataframe making it ready for Summary.from_pandas()

    * Ensures that the index is always datetime, and sorted.
    * Removes BLOCK vectors, these are currently not supported as
      it requires knowledge of the grid dimensions. Warnings
      will be emitted for skipped columns

    Args:
        dframe: Dataframe to read. Will not be modified.

    Returns:
        Modified copy of incoming dataframe.
    """
    if dframe.empty:
        return dframe
    dframe = dframe.copy()
    if "DATE" in dframe.columns:
        # Infer datatype (Pandas cannot answer it) based on the first element:
        if isinstance(dframe["DATE"].to_numpy()[0], str):
            # Do not use pd.Series.apply() here, Pandas would try to convert it to
            # datetime64[ns] which is limited at year 2262.
            dframe["DATE"] = pd.Series(
                [dateutil.parser.parse(datestr) for datestr in dframe["DATE"]],
                dtype="object",
                index=dframe.index,
            )
        if isinstance(dframe["DATE"].to_numpy()[0], dt.date):
            dframe["DATE"] = pd.Series(
                [
                    dt.datetime.combine(dateobj, dt.datetime.min.time())
                    for dateobj in dframe["DATE"]
                ],
                dtype="object",
                index=dframe.index,
            )

        dframe = dframe.set_index("DATE")
    if not isinstance(
        dframe.index.to_numpy()[0], (dt.datetime, np.datetime64, pd.Timestamp)
    ):
        raise ValueError(
            "dataframe must have a datetime index, got "
            f"{dframe.index.to_numpy()[0]} of type {type(dframe.index.to_numpy()[0])}"
        )
    dframe = dframe.sort_index(axis=0)

    # This column will appear if dataframes are naively written to CSV
    # files and read back in again.
    if "Unnamed: 0" in dframe:
        dframe = dframe.drop("Unnamed: 0", axis="columns")

    block_columns = [
        col for col in dframe.columns if (col.startswith("B") or col.startswith("LB"))
    ]
    if block_columns:
        dframe = dframe.drop(columns=block_columns)
        logger.warning(
            "Dropped columns with block data, not supported: %s",
            {colname.partition(":")[0] + ":*" for colname in block_columns},
        )

    return dframe


def df2ressum(
    dframe: pd.DataFrame,
    casename: str = "SYNTHETIC",
) -> Summary:
    """Convert a dataframe to a Summary object

    Args:
        dframe: Dataframe with a DATE colum (or with the
            dates/datetimes in the index).
        casename: Name of casename/basename to be used for the Summary object
            If the Summary object is later written to disk, this will be used
            to construct the filenames.
    """
    if dframe.empty:
        return None

    if casename.upper() != casename:
        raise ValueError(f"casename {casename} must be UPPER CASE")
    if "." in casename:
        raise ValueError(f"Do not use dots in casename {casename}")

    dframe = _fix_dframe_for_resdata(dframe)
    return Summary.from_pandas(casename, dframe)


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser: parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE",
        help="Name of the .DATA input file for the reservoir simulator."
        " There must exist a UNSMRY file with the same path and basename.",
    )
    parser.add_argument(
        "--time_index",
        type=str,
        help=(
            "Time resolution mnemonic; raw, daily, monthly or yearly. "
            "Data at a given point in time applies until the next point in time. "
            "If not raw, data will be interpolated. Use interpolated rate vectors "
            "with care. Default is raw, which will include clock times. first and last "
            "are also accepted and will print data for the first or the last date. "
        ),
        default="raw",
    )
    parser.add_argument(
        "--column_keys",
        nargs="+",
        help=(
            "Summary column vector wildcards, space-separated. "
            "Default is to include all summary vectors available."
        ),
    )
    parser.add_argument(
        "--start_date",
        type=str,
        help=(
            "Start at a specific date, in ISO format YYYY-MM-DD. "
            "Ignored if time_index is first or last"
        ),
        default="",
    )

    parser.add_argument(
        "--end_date",
        type=str,
        help=(
            "End at a specific date, in ISO format YYYY-MM-DD. "
            "Ignored if time_index is first or last"
        ),
        default="",
    )
    parser.add_argument(
        "-p",
        "--params",
        action="store_true",
        help="Merge key-value data from parameter file into each row.",
    )
    parser.add_argument(
        "--paramfile",
        type=str,
        help=(
            "Filename of key-value parameter file to look for if -p is set, "
            "relative to simulator input (.DATA) file or an absolute filename. "
            "If not supplied, parameters.{json,yml,txt} in "
            "{., .. and ../..} will be merged in."
        ),
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=("Name of output file. Use '-' to write to stdout. Default 'summary.csv'"),
        default="summary.csv",
    )
    parser.add_argument("--arrow", action="store_true", help="Write to pyarrow format")
    parser.add_argument(
        "--include_restart",
        action="store_true",
        help="Attempt to include data from before restart",
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def fill_reverse_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Fill a parser for the operation:  dataframe -> summary files"""

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Basename for output files",
        default="SYNTSMRY",
    )
    parser.add_argument("csvfile", help="Name of CSV file with summary data.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument("--debug", action="store_true", help="Be verbose")
    return parser


def summary_main(args: argparse.Namespace) -> None:
    """Read summary data from disk and write CSV back to disk"""
    logger = getLogger_res2csv(__name__, vars(args))
    eclbase = (
        args.DATAFILE.replace(".DATA", "").replace(".UNSMRY", "").replace(".SMSPEC", "")
    )

    resdatafiles = ResdataFiles(eclbase)
    sum_df = df(
        resdatafiles,
        time_index=args.time_index,
        column_keys=args.column_keys,
        start_date=args.start_date,
        end_date=args.end_date,
        include_restart=args.include_restart,
        params=args.params,
        paramfile=args.paramfile,
        datetime=False,
    )

    if sum_df.empty:
        logger.error("No data to write. The input file may be missing or invalid.")
        return

    if args.arrow:
        sum_df = _df2pyarrow(sum_df)

    write_dframe_stdout_file(sum_df, args.output, index=True, caller_logger=logger)


def summary_reverse_main(args: argparse.Namespace) -> None:
    """Entry point for usage with "csv2res summary" on the command line"""
    logger = getLogger_res2csv(__name__, vars(args))

    summary_df = pd.read_csv(args.csvfile)
    logger.info("Parsed %s", args.csvfile)

    outputdir = Path(args.output).parent
    eclbase = Path(args.output).name

    # Summary.fwrite() can only write to current directory:
    cwd = Path.cwd()
    summary = df2ressum(summary_df, eclbase)
    try:
        os.chdir(outputdir)
        Summary.fwrite(summary)
    finally:
        os.chdir(cwd)

    logger.info("Wrote to %s and %s", args.output + ".UNSMRY", args.output + ".SMSPEC")
