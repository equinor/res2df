import pandas as pd
from typing import Optional
from dataclasses import dataclass
from typing import Union, List
from pathlib import Path
import math
import six

from ecl.summary import EclSum
from ert.util import CTime


@dataclass
class EclipseVectorDefinition:
    raw_key: str
    full_key: str
    main_key: str
    unit: str
    num: Optional[int] = 0
    well_or_group_key: Optional[str] = None


def _get_ecl_key(column: str, unit_system: str = "METRIC"):
    # Return a list of eclipse str keys for use in EclSum.addVariable
    # The names/columns may be in the formats
    # FOPR
    # GOPR:grpname or WOPR:wellname and so forth
    # "BPR:13,2,6", i.e. if commas are used to specify grid cell indices, "" needs to be used in csv
    if not unit_system == "METRIC":
        raise ValueError(
            f'Unit system {unit_system} not suppoerted, use (yet) supported, use "METRIC"'
        )

    # Check if surrounded by "" (e.g. cell parameters)
    tmp = column.split(sep='"')
    name_to_use = tmp[1] if len(tmp) == 3 else column

    if ":" in name_to_use:
        main_key, sub_key = name_to_use.split(sep=":")
    else:
        main_key, sub_key = name_to_use, None

    well_or_group, num = None, 0
    if sub_key:
        try:
            num = int(sub_key)
        except ValueError:
            well_or_group = sub_key

    if EclSum.is_rate(main_key):
        unit = "Sm3/day"
    elif EclSum.is_total(main_key):
        unit = "Sm3"
    else:
        # Todo - check if there is functionality to check other vectors which type they are
        # Ideally: libecl have a method get_key_type(key: str) which returns rate, total, pressure et.c...
        # and another method for get_type_unit(unit_system) which returns e.g. Sm3/day for rates et.c. if unit_system is metric
        unit = None

    return EclipseVectorDefinition(
        raw_key=column,
        full_key=name_to_use,
        main_key=main_key,
        well_or_group_key=well_or_group,
        unit=unit,
        num=num,
    )


SECONDS_PER_DAY = 86400.0


def _time_delta_to_days(timedelta: pd.Timedelta) -> float:
    return timedelta.total_seconds() / SECONDS_PER_DAY


def df2summary(
    data_frame: pd.DataFrame,
    case_name: str,
):
    # Dates should be index of dataframe
    data_frame_sorted = data_frame.sort_index(axis=0)
    dates = data_frame_sorted.index
    days_from_start = [_time_delta_to_days(timestep - dates[0]) for timestep in dates]
    dates_ctime = [CTime(date) for date in data_frame_sorted.index]

    dummy_grid_resolution = (20, 10, 5)
    eclsum = EclSum.restart_writer(
        case=case_name,
        restart_case=None,
        restart_step=-1,
        start_time=dates_ctime[0],
        nx=dummy_grid_resolution[0],
        ny=dummy_grid_resolution[1],
        nz=dummy_grid_resolution[2],
    )

    columns = data_frame_sorted.columns.values
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
            tstep[vector.full_key] = data_frame_sorted.get(vector.raw_key)[report_step]

    EclSum.fwrite(eclsum)


def read_time_series_csv_file(
    file_path: Union[str, Path], vectors: List[str] = None
) -> pd.DataFrame:

    vectors_uppercase = (
        ["DATES", "DATE"] + [x.upper() for x in vectors]
        if vectors is not None
        else None
    )
    usecols = (
        None
        if vectors is None
        else lambda x: x.upper().replace(" ", "") in vectors_uppercase
    )
    dataframe = pd.read_csv(
        file_path,
        index_col=0,
        skipinitialspace=True,
        parse_dates=True,
        dayfirst=True,
        comment="#",
        usecols=usecols,
    )

    # Remove emtry lines (sometimes lines with ,,, are exported from Excel)
    dataframe.dropna(axis=0, how="all", inplace=True)

    # Remove space from column names
    cols = dataframe.columns.map(
        lambda x: x.replace(" ", "") if isinstance(x, (str, six.text_type)) else x
    )
    dataframe.columns = cols

    # The read_csv() method seems to "work" for any input;
    # here we raise an exception if we get a frame with one
    # element in it - which is Nan.
    if len(dataframe) <= 1:
        col0 = dataframe[dataframe.columns[0]]
        if math.isnan(col0[0]):
            raise Exception("Could not load pandas frame from:{}".format(file_path))

    return dataframe
