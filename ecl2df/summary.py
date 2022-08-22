"""Provide a two-way Pandas DataFrame interface to Eclipse summary data (UNSMRY)"""
import argparse
import ctypes

# The name 'datetime' is in use by a function argument:
import datetime as dt
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import dateutil
import numpy as np
import pandas as pd
import pyarrow
import pyarrow.feather
from ecl.summary import EclSum, EclSumKeyWordVector

from ecl2df import getLogger_ecl2csv

from . import parameters
from .common import write_dframe_stdout_file
from .eclfiles import EclFiles

logger: logging.Logger = logging.getLogger(__name__)

# Frequency mnemonics for the API consumer to use:
FREQ_RAW: str = "raw"
FREQ_FIRST: str = "first"
FREQ_LAST: str = "last"
PD_FREQ_MNEMONICS: Dict[str, str] = {
    "daily": "D",
    "weekly": "W-MON",
    "monthly": "MS",
    "yearly": "YS",
    # Any frequency mnemonics not mentioned here will be
    # passed on to Pandas.
}
"""Mapping from ecl2df custom offset strings to Pandas DateOffset strings.
See
https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#dateoffset-objects
"""  # noqa


def date_range(start_date: dt.date, end_date: dt.date, freq: str) -> List[dt.datetime]:
    """Wrapper for pandas.date_range to allow for extra ecl2df specific mnemonics
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


def _ensure_date_or_none(some_date: Optional[Union[str, dt.date]]) -> Optional[dt.date]:
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
    if some_date == "":
        return None
    if isinstance(some_date, str):
        return dateutil.parser.parse(some_date).date()  # type: ignore
    raise TypeError(f"some_date must be a string or a date, got {some_date}")


def _crop_datelist(
    eclsumsdates: List[dt.datetime],
    freq: Union[dt.date, dt.datetime, str],
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
) -> Union[List[dt.date], List[dt.datetime]]:
    """Helper function for resample_smry_dates, taking care of
    the special cases where the list of dates should not be resampled, but
    only cropped or returned as is.

    Args:
        eclsumsdates: list of datetimes, typically coming from EclSum.dates
        freq: Either a date or datetime, or a frequency string
            "raw", "first" or "last".
        start_date: Dates prior to this date will be cropped.
        end_date: Dates after this date will be cropped.

    Returns:
        list of datetimes.
    """
    datetimes: Union[List[dt.date], List[dt.datetime]] = []  # type: ignore
    if freq == FREQ_RAW:
        datetimes = eclsumsdates
        datetimes.sort()
        if start_date:
            # Convert to datetime (at 00:00:00)
            start_date = dt.datetime.combine(start_date, dt.datetime.min.time())
            datetimes = [x for x in datetimes if x > start_date]
            datetimes = [start_date] + datetimes
        if end_date:
            end_date = dt.datetime.combine(end_date, dt.datetime.min.time())
            datetimes = [x for x in datetimes if x < end_date]
            datetimes = datetimes + [end_date]
    elif freq == FREQ_FIRST:
        datetimes = [min(eclsumsdates).date()]
    elif freq == FREQ_LAST:
        datetimes = [max(eclsumsdates).date()]
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
            ) + dateutil.relativedelta.relativedelta(  # type: ignore
                months=1
            )
        return dt.datetime(year=rollme.year, month=rollme.month, day=1)

    raise ValueError(
        "Only yearly or monthly frequencies are "
        "supported for simulations beyond year 2262"
    )


def _fallback_date_range(start: dt.date, end: dt.date, freq: str) -> List[dt.datetime]:
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
            dates = dates + [dt.datetime.combine(end, dt.datetime.min.time())]
        return dates
    if freq == "monthly":
        dates = []
        date = dt.datetime.combine(start, dt.datetime.min.time())
        enddatetime = dt.datetime.combine(end, dt.datetime.min.time())
        while date <= enddatetime:
            dates.append(date)
            date = date + dateutil.relativedelta.relativedelta(months=1)  # type: ignore
        return dates
    raise ValueError("Unsupported frequency for datetimes beyond year 2262")


def resample_smry_dates(
    eclsumsdates: List[dt.datetime],
    freq: str = FREQ_RAW,
    normalize: bool = True,
    start_date: Optional[Union[str, dt.date]] = None,
    end_date: Optional[Union[str, dt.date]] = None,
) -> Union[List[dt.date], List[dt.datetime]]:
    """
    Resample (optionally) a list of date(time)s to a new datelist according to options.

    Based on the dates as input, a new list at a finer or coarser time density
    can be returned, on the same date range. Incoming dates can also be cropped.

    Args:
        eclsumsdates: list of datetimes, typically coming from EclSum.dates
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
        return _crop_datelist(eclsumsdates, freq, start_date, end_date)

    # In case freq is an ISO-date(time)-string, interpret as such:
    try:
        parseddate = dateutil.parser.isoparse(freq)  # type: ignore
        return [parseddate]
    except ValueError:
        # freq is a frequency string or datetime.date (or similar)
        pass

    # These are datetime.datetime, not datetime.date
    start_smry = min(eclsumsdates)
    end_smry = max(eclsumsdates)

    # Normalize start and end date according to frequency by extending the time range.
    # [1997-11-05, 2020-03-02] and monthly frequecy
    # will be mapped to [1997-11-01, 2020-04-01]
    # For yearly frequency it will return [1997-01-01, 2021-01-01].
    offset = pd.tseries.frequencies.to_offset(PD_FREQ_MNEMONICS.get(freq, freq))
    try:
        start_normalized = offset.rollback(start_smry.date()).date()
    except pd.errors.OutOfBoundsDatetime:
        # Pandas only supports datetime up to year 2262
        start_normalized = _fallback_date_roll(start_smry, "back", freq).date()
    try:
        end_normalized = offset.rollforward(end_smry.date()).date()
    except pd.errors.OutOfBoundsDatetime:
        # Pandas only supports datetime up to year 2262
        end_normalized = _fallback_date_roll(end_smry, "forward", freq).date()

    if start_date is None:
        if normalize:
            start_date_range = start_normalized
        else:
            start_date_range = start_smry.date()
    else:
        # Normalization is not applied for explicit date
        start_date_range = start_date

    if end_date is None:
        if normalize:
            end_date_range = end_normalized
        else:
            end_date_range = end_smry.date()
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
        dates = [start_date] + dates
    if end_date and end_date not in dates:
        dates = dates + [end_date]
    return dates


def df(
    eclfiles: EclFiles,
    time_index: Optional[str] = None,
    column_keys: Union[List[str], str] = None,
    start_date: Optional[Union[str, dt.date]] = None,
    end_date: Optional[Union[str, dt.date]] = None,
    include_restart: bool = True,
    params: bool = False,
    paramfile: Optional[str] = None,
    datetime: bool = False,  # A very poor choice of argument name [pylint]
):
    # pylint: disable=too-many-arguments
    """
    Extract data from UNSMRY as Pandas dataframes.

    This is a thin wrapper for EclSum.pandas_frame, by adding
    support for string mnenomics for the time index.

    The dataframe is always indexed by DATE, and the datatype for the
    index will usually be datetime64[ns] as long as all dates are
    before year 2262. If a longer time range is detected, the index.dtype
    will be object, and consisting of datetime.datetime() objects. The index
    is always named "DATE".

    Arguments:
        eclfiles: EclFiles object representing the Eclipse deck. Alternatively
           an EclSum object.
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
        include_restart: boolean sent to libecl for wheter restarts
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

    if isinstance(eclfiles, EclSum):
        eclsum = eclfiles
    else:
        try:
            eclsum = eclfiles.get_eclsum(include_restart=include_restart)
        except OSError:
            logger.warning("Error reading summary instance, returning empty dataframe")
            return pd.DataFrame()

    time_index_arg: Optional[Union[List[dt.date], List[dt.datetime]]]
    if isinstance(time_index, str) and time_index == "raw":
        time_index_arg = resample_smry_dates(
            eclsum.dates,
            "raw",
            False,
            start_date,
            end_date,
        )
    elif isinstance(time_index, str):
        time_index_arg = resample_smry_dates(
            eclsum.dates,
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

    # dframe = eclsum.pandas_frame(time_index_arg, column_keys)
    dframe = _libecl_eclsum_pandas_frame(eclsum, time_index_arg, column_keys)

    logger.info(
        "Dataframe with smry data ready, %d columns and %d rows",
        len(dframe.columns),
        len(dframe),
    )
    dframe.index.name = "DATE"
    if params or paramfile:
        dframe = _merge_params(dframe, paramfile, eclfiles)

    # Add metadata as an attribute the dataframe, using experimental Pandas features:
    meta = smry_meta(eclsum)
    # Slice meta to dataframe columns:
    dframe.attrs["meta"] = {
        column_key: meta[column_key] for column_key in dframe if column_key in meta
    }

    # Remove duplicated column names. These will occur from libecl
    # when the user has repeated vector names in the summary SECTION
    dupes = dframe.columns.duplicated()
    if dupes.any():
        logger.warning(
            "Duplicated columns detected, check your DATA file "
            "for repeated vectors in the SUMMARY section"
        )
        logger.warning("Duplicates: %s", list(dframe.columns[dupes]))
        dframe = dframe.loc[:, ~dframe.columns.duplicated()]

    dframe = _ensure_unique_datetime_index(dframe)

    if datetime is True:
        if dframe.index.dtype == "object":
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
                "Dataframe of smry data contained duplicate timestamps due to limited",
                " output resolution. Vector TIMESTEP exists, utilizing it to create "
                "discrete timestamps",
                f"Original duplicates were:{index_duplicate_log_string}",
            )
            index_as_list = dframe.index.to_list()

            if dframe.attrs["meta"]["TIMESTEP"]["unit"] == "DAYS":
                for idx in np.where(index_duplicates)[0]:
                    index_as_list[idx] = index_as_list[idx] + dt.timedelta(
                        days=dframe["TIMESTEP"][idx]
                    )
            elif dframe.attrs["meta"]["TIMESTEP"]["unit"] == "HOURS":
                for idx in np.where(index_duplicates)[0]:
                    index_as_list[idx] = index_as_list[idx] + dt.timedelta(
                        hours=dframe["TIMESTEP"][idx]
                    )
            else:
                raise ValueError(
                    "Dataframe of smry data contained duplicate timestamps",
                    "Vector TIMESTEP exists, but unit could not be identified",
                )
            dframe.index = index_as_list
        else:
            raise ValueError(
                "Dataframe of smry data contained duplicate timestamps due to limited.",
                " output resolution. Vector TIMESTEP was not found. Try to add it to ",
                "the SUMMARY section of the simulation deck, as it may be utilized to",
                " separate duplicate timestamps.",
            )
    return dframe


def _df2pyarrow(dframe: pd.DataFrame) -> pyarrow.Table:
    """Construct a Pyarrow table from a dataframe, conserving metadata.

    All integer columns will have datatype int32, all floats will have float32
    as this is Eclipse specific.

    Metadata values will be written as strings. A True property is thus
    represented as the string "True" in the arrow object.

    The index in the dataframe is always assumed to be a time-index, but
    not necessarily a Pandas datetimetype (which is only of nanosecond precision).
    This index is always named DATE in the pyarrow table.
    """

    field_list: List[pyarrow.Field] = []
    field_list.append(pyarrow.field("DATE", pyarrow.timestamp("ms")))
    column_arrays = [dframe.index.to_numpy().astype("datetime64[ms]")]

    for colname in dframe.columns:
        if "meta" in dframe.attrs and colname in dframe.attrs["meta"]:
            # Boolean objects in the metadata dictionary must be converted to bytes:
            field_metadata = {
                bytes(key, encoding="ascii"): bytes(str(value), encoding="ascii")
                for key, value in dframe.attrs["meta"][colname].items()
            }
        else:
            field_metadata = {}
        if pd.api.types.is_integer_dtype(dframe.dtypes[colname]):
            dtype = pyarrow.int32()
        elif pd.api.types.is_string_dtype(dframe.dtypes[colname]):
            # Parameters are potentially merged into the dataframe.
            dtype = pyarrow.string()
        else:
            dtype = pyarrow.float32()
        field_list.append(pyarrow.field(colname, dtype, metadata=field_metadata))
        column_arrays.append(dframe[colname].to_numpy())

    schema = pyarrow.schema(field_list)

    return pyarrow.table(column_arrays, schema=schema)


def _merge_params(
    dframe: pd.DataFrame,
    paramfile: Optional[Union[str, Path]] = None,
    eclfiles: Union[str, EclFiles] = None,
) -> pd.DataFrame:
    """Locate parameters in a <key> <value> file and add to the dataframe.

    Will fetch parameters directly from a text file if provided, or look up
    the parameters.txt file based on the location of an Eclise run.
    """

    if paramfile is None and eclfiles is not None:
        param_files = parameters.find_parameter_files(eclfiles)
        logger.info("Loading parameters from files: %s", str(param_files))
        param_dict = parameters.load_all(param_files)
    elif (
        paramfile is not None
        and eclfiles is not None
        and not Path(paramfile).is_absolute()
    ):
        param_files = parameters.find_parameter_files(eclfiles, filebase=str(paramfile))
        logger.info("Loading parameters from files: %s", str(param_files))
        param_dict = parameters.load_all(param_files)
    elif paramfile is not None and Path(paramfile).is_absolute():
        logger.info("Loading parameters from file: %s", str(paramfile))
        param_dict = parameters.load(paramfile)
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


def smry_meta(eclfiles: EclFiles) -> Dict[str, Dict[str, Any]]:
    """Provide metadata for summary data vectors.

    A dictionary indexed by summary vector name is returned, and each
    value is dictionary with the metadata types provided by the underlying
    EclSum object:

    * unit (string)
    * is_total (bool)
    * is_rate (bool)
    * is_historical (bool)
    * get_num (int) (only provided if not None)
    * keyword (str)
    * wgname (str or None)
    """
    if isinstance(eclfiles, EclSum):
        eclsum = eclfiles
    else:
        eclsum = eclfiles.get_eclsum()

    meta: Dict[str, Dict[str, Any]] = {}
    for col in eclsum.keys():
        meta[col] = {}
        meta[col]["unit"] = eclsum.unit(col)
        meta[col]["is_total"] = eclsum.is_total(col)
        meta[col]["is_rate"] = eclsum.is_rate(col)
        meta[col]["is_historical"] = eclsum.smspec_node(col).is_historical()
        meta[col]["keyword"] = eclsum.smspec_node(col).keyword
        meta[col]["wgname"] = eclsum.smspec_node(col).wgname
        num = eclsum.smspec_node(col).get_num()
        if num is not None:
            meta[col]["get_num"] = num
    return meta


def _fix_dframe_for_libecl(dframe: pd.DataFrame) -> pd.DataFrame:
    """Fix a dataframe making it ready for EclSum.from_pandas()

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
        if isinstance(dframe["DATE"].values[0], str):
            # Do not use pd.Series.apply() here, Pandas would try to convert it to
            # datetime64[ns] which is limited at year 2262.
            dframe["DATE"] = pd.Series(
                [
                    dateutil.parser.parse(datestr)  # type: ignore
                    for datestr in dframe["DATE"]
                ],
                dtype="object",
                index=dframe.index,
            )
        if isinstance(dframe["DATE"].values[0], dt.date):
            dframe["DATE"] = pd.Series(
                [
                    dt.datetime.combine(dateobj, dt.datetime.min.time())
                    for dateobj in dframe["DATE"]
                ],
                dtype="object",
                index=dframe.index,
            )

        dframe.set_index("DATE", inplace=True)
    if not isinstance(
        dframe.index.values[0], (dt.datetime, np.datetime64, pd.Timestamp)
    ):
        raise ValueError(
            "dataframe must have a datetime index, got "
            f"{dframe.index.values[0]} of type {type(dframe.index.values[0])}"
        )
    dframe.sort_index(axis=0, inplace=True)

    # This column will appear if dataframes are naively written to CSV
    # files and read back in again.
    if "Unnamed: 0" in dframe:
        dframe.drop("Unnamed: 0", axis="columns", inplace=True)

    block_columns = [
        col for col in dframe.columns if (col.startswith("B") or col.startswith("LB"))
    ]
    if block_columns:
        dframe = dframe.drop(columns=block_columns)
        logger.warning(
            "Dropped columns with block data, not supported: %s",
            str({colname.partition(":")[0] + ":*" for colname in block_columns}),
        )

    return dframe


def df2eclsum(
    dframe: pd.DataFrame,
    casename: str = "SYNTHETIC",
) -> EclSum:
    """Convert a dataframe to an EclSum object

    Args:
        dframe: Dataframe with a DATE colum (or with the
            dates/datetimes in the index).
        casename: Name of Eclipse casename/basename to be used for the EclSum object
            If the EclSum object is later written to disk, this will be used
            to construct the filenames.
    """
    if dframe.empty:
        return None

    if casename.upper() != casename:
        raise ValueError(f"casename {casename} must be UPPER CASE")
    if "." in casename:
        raise ValueError(f"Do not use dots in casename {casename}")

    dframe = _fix_dframe_for_libecl(dframe)
    return _libecl_eclsum_from_pandas(casename, dframe)
    # return EclSum.from_pandas(casename, dframe)


def _libecl_eclsum_pandas_frame(
    eclsum: EclSum,
    time_index: Optional[Union[List[dt.date], List[dt.datetime]]] = None,
    column_keys: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Build a Pandas dataframe from an EclSum object.

    Temporarily copied from libecl to circumvent bug

    https://github.com/equinor/ecl/issues/802
    """
    if column_keys is None:
        keywords = EclSumKeyWordVector(eclsum, add_keywords=True)
    else:
        keywords = EclSumKeyWordVector(eclsum)
        for key in column_keys:
            keywords.add_keywords(key)

    # pylint: disable=protected-access
    if time_index is None:
        time_index = eclsum.dates  # Changed from libecl
        data = np.zeros([len(time_index), len(keywords)])
        EclSum._init_pandas_frame(
            eclsum, keywords, data.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        )
    else:
        time_points = eclsum._make_time_vector(time_index)
        data = np.zeros([len(time_points), len(keywords)])
        EclSum._init_pandas_frame_interp(
            eclsum,
            keywords,
            time_points,
            data.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )

    # Do not give datetime64[ms] to Pandas, it will try to convert it
    # to datetime64[ns] and error hard if it is out of bounds (year 2262)
    assert isinstance(time_index[0], (dt.date, dt.datetime))
    frame = pd.DataFrame(
        index=time_index,
        columns=list(keywords),
        data=data,
    )

    # frame.index.type is now either datetime64[ns] or datetime.datetime (object)
    # depending on whether the date range ended before 2262.
    return frame


def _libecl_eclsum_from_pandas(
    case: str,
    frame: pd.DataFrame,
    dims: Optional[List[int]] = None,
    headers: Optional[List[tuple]] = None,
) -> EclSum:
    """Build an EclSum object from a Pandas dataframe.

    Temporarily copied from libecl to circumvent bug

    https://github.com/equinor/ecl/issues/802
    """
    start_time = frame.index[0]

    # Avoid Pandas or numpy timestamps, to avoid limitations
    # to timestamp64[ns] date boundaries (year 2262)
    if isinstance(start_time, pd.Timestamp):
        start_time = start_time.to_pydatetime()

    var_list = []
    # pylint: disable=protected-access
    if headers is None:
        header_list = EclSum._compile_headers_list(frame.columns.values, dims)
    else:
        header_list = EclSum._compile_headers_list(headers, dims)
    if dims is None:
        dims = [1, 1, 1]
    ecl_sum = EclSum.writer(case, start_time, dims[0], dims[1], dims[2])
    for keyword, wgname, num, unit in header_list:
        var_list.append(
            ecl_sum.addVariable(keyword, wgname=wgname, num=num, unit=unit).getKey1()
        )

    for idx, time in enumerate(frame.index):
        days = (time - start_time).days
        t_step = ecl_sum.addTStep(idx + 1, days)
        for var in var_list:
            t_step[var] = frame.iloc[idx][var]
    return ecl_sum


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser: parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE",
        help="Name of Eclipse DATA file. " + "UNSMRY file must lie alongside.",
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
            "relative to Eclipse DATA file or an absolute filename. "
            "If not supplied, parameters.{json,yml,txt} in "
            "{., .. and ../..} will be merged in."
        ),
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=(
            "Name of output file. Use '-' to write to stdout. " "Default 'summary.csv'"
        ),
        default="summary.csv",
    )
    parser.add_argument("--arrow", action="store_true", help="Write to pyarrow format")

    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def fill_reverse_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Fill a parser for the operation:  dataframe -> eclsum files"""

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Basename for Eclipse output files",
        default="SYNTSMRY",
    )
    parser.add_argument("csvfile", help="Name of CSV file with summary data.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument("--debug", action="store_true", help="Be verbose")
    return parser


def summary_main(args) -> None:
    """Read summary data from disk and write CSV back to disk"""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    eclbase = (
        args.DATAFILE.replace(".DATA", "").replace(".UNSMRY", "").replace(".SMSPEC", "")
    )

    eclfiles = EclFiles(eclbase)
    sum_df = df(
        eclfiles,
        time_index=args.time_index,
        column_keys=args.column_keys,
        start_date=args.start_date,
        end_date=args.end_date,
        params=args.params,
        paramfile=args.paramfile,
        datetime=False,
    )
    if args.arrow:
        sum_df = _df2pyarrow(sum_df)

    write_dframe_stdout_file(sum_df, args.output, index=True, caller_logger=logger)


def summary_reverse_main(args) -> None:
    """Entry point for usage with "csv2ecl summary" on the command line"""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )

    summary_df = pd.read_csv(args.csvfile)
    logger.info("Parsed %s", args.csvfile)

    outputdir = Path(args.output).parent
    eclbase = Path(args.output).name

    # EclSum.fwrite() can only write to current directory:
    cwd = os.getcwd()
    eclsum = df2eclsum(summary_df, eclbase)
    try:
        os.chdir(outputdir)
        EclSum.fwrite(eclsum)
    finally:
        os.chdir(cwd)

    logger.info("Wrote to %s and %s", args.output + ".UNSMRY", args.output + ".SMSPEC")
