"""Implementation of :func:`summary_pandas_frame`, a replacement for
``resdata.summary.Summary.pandas_frame`` which can also read the summary
files directly (using ``resfo_utilities``) when no ``Summary`` object
has been constructed by the caller.
"""

import fnmatch
import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import pairwise
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pandas as pd
from natsort import natsorted
from resdata.summary import Summary
from resfo_utilities import (
    InvalidSummaryError,
    InvalidSummaryKeyError,
    SummaryKeyType,
    SummaryKeyword,
    SummaryReader,
    is_rate,
    make_summary_key,
)

_EPOCH = datetime(1970, 1, 1)
_DEFAULT_VALUE = -99.0
_SECONDS_PER_UNIT = {"DAYS": 24 * 3600, "HOURS": 3600}
# Name of the unused well/group slots eclipse writes to the smspec
_DUMMY_NAME = ":+:+:+:+"
_WELL = SummaryKeyType.WELL
_GROUP = SummaryKeyType.GROUP


def summary_pandas_frame(
    summary: Summary | str | os.PathLike[str],
    time_index: Sequence[datetime | date] | None = None,
    column_keys: Sequence[str] | None = None,
    include_restart: bool = True,
) -> pd.DataFrame:
    """Create a pandas frame with summary data.

    The result is equivalent to ``Summary.pandas_frame``, ie. by default
    one row for each time point (including ministeps) in the summary case,
    or the values interpolated to ``time_index`` if given. Rates are
    given as step functions (0 outside the simulated range) while other
    values are linearly interpolated (and constant outside the simulated range).

    Args:
        summary: Either a ``resdata.summary.Summary`` object, in which case
            ``Summary.pandas_frame`` is used, or the name of a summary case.
            The case can be the basename (``path/to/CASE``), a summary file
            (``path/to/CASE.UNSMRY``), or a directory with exactly one
            ``.DATA`` file (``path/to/``).
        time_index: Times to interpolate to, default is the times in the summary.
        column_keys: List of key patterns (wildcards ``*`` etc. allowed),
            default is all summary vectors.
        include_restart: If the case is a restart, whether to also include
            data from the case it was restarted from. Ignored if ``summary``
            is a ``Summary`` object, as that is decided on construction.

    Raises:
        FileNotFoundError: If no summary files were found for the given case.
        InvalidSummaryError: If the summary files have invalid contents.
    """
    if isinstance(summary, Summary):
        return summary.pandas_frame(time_index, column_keys)
    cases = _read_cases(os.fspath(summary), include_restart)
    main = cases[0]
    chosen = _select_columns(main, column_keys)
    columns = [name for name, _ in chosen]
    selected = [i for _, i in chosen]
    rates = np.array([main.rates[i] for i in selected], dtype=bool)
    times, values = _merge(
        [_read_block(case, main, selected) for case in cases], len(selected)
    )
    # The data arrays are not shared, so no need for pandas to copy them
    if time_index is None:
        index = pd.DatetimeIndex(times.astype("datetime64[s]")).as_unit("us")
        return pd.DataFrame(index=index, columns=columns, data=values, copy=False)
    requested = np.array([_to_time_t(t) for t in time_index], dtype=np.int64)
    return pd.DataFrame(
        index=list(time_index),
        columns=columns,
        data=_interpolate(times, values, rates, requested),
        copy=False,
    )


def _to_time_t(time: datetime | date) -> int:
    """Seconds since epoch, ignoring fractions of seconds and time zone."""
    naive = datetime(
        time.year,
        time.month,
        time.day,
        getattr(time, "hour", 0),
        getattr(time, "minute", 0),
        getattr(time, "second", 0),
    )
    return (naive - _EPOCH) // timedelta(seconds=1)


@dataclass
class _Case:
    """The layout of one case (smspec) and the reader for its summary files.

    Attributes:
        reader: Reader for the summary files of the case.
        keys: The summary key for each parameter, None if invalid.
        by_key: The last parameter index for each key.
        rates: Whether each parameter is a rate.
        time_param: The index of the TIME parameter.
        time_unit: The number of seconds per unit of TIME.
        restart: Path of the case this case was restarted from.
    """

    reader: SummaryReader
    keys: list[str | None]
    by_key: dict[str, int]
    keywords: list[SummaryKeyword]
    rates: list[bool]
    time_param: int
    time_unit: int
    restart: str | None


def _read_block(
    case: _Case, main: _Case, selected: list[int]
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]:
    """The times and values for the selected parameters of the main case.

    Only the needed parameters are kept while reading. Parameters
    not present in the case gets the default value.
    """
    source = [
        param if case is main else case.by_key.get(main.keys[param] or "")
        for param in selected
    ]
    found = [i for i, src in enumerate(source) if src is not None]
    times, values = _read_values(case, [src for src in source if src is not None])
    if len(found) == len(selected):
        return times, values
    block = np.full((len(times), len(selected)), _DEFAULT_VALUE)
    block[:, found] = values
    return times, block


def _read_values(
    case: _Case, params: list[int]
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]:
    """The time (in seconds since epoch) and values for each step."""
    columns = np.array([case.time_param, *params], dtype=np.intp)
    data = np.empty((256, len(columns)), dtype=np.float32)
    steps = 0
    for row in case.reader.values(report_step_only=False):
        if len(row) != len(case.keys):
            raise InvalidSummaryError(
                f"Expected {len(case.keys)} parameters in each step, got {len(row)}"
            )
        if steps == len(data):
            data.resize((2 * steps, len(columns)), refcheck=False)
        data[steps] = row[columns]
        steps += 1
    data = data[:steps]
    # resdata ignores the time of day in STARTDAT
    start_time = _to_time_t(case.reader.start_date.date())
    times = np.trunc(start_time + data[:, 0].astype(np.float64) * case.time_unit)
    return times.astype(np.int64), data[:, 1:].astype(np.float64)


def _merge(
    blocks: list[tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]], width: int
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]:
    """Merge the times and values of the cases (the first being the main case).

    The cases are ordered by their start, and each case is cut
    where the next one starts.
    """
    ordered = sorted((b for b in blocks if len(b[0]) > 0), key=lambda b: b[0][0])
    if not ordered:
        return np.zeros(0, dtype=np.int64), np.zeros((0, width))
    ends = [
        int(np.searchsorted(times, next_times[0], "left"))
        for (times, _), (next_times, _) in pairwise(ordered)
    ] + [len(ordered[-1][0])]
    parts = [
        (times[:end], values[:end])
        for (times, values), end in zip(ordered, ends, strict=True)
    ]
    if len(parts) == 1:
        return parts[0]
    return np.concatenate([t for t, _ in parts]), np.concatenate([v for _, v in parts])


def _read_cases(case: str, include_restart: bool) -> list[_Case]:
    """The case and the cases it was restarted from."""
    files: list[_Case] = []
    visited: set[Path] = set()
    current: str | None = case
    while current and Path(current).resolve() not in visited:
        try:
            reader = _open_reader(current)
        except FileNotFoundError:
            if not files:
                raise
            break
        files.append(_read_layout(reader))
        visited.add(Path(current).resolve())
        current = files[-1].restart if include_restart else None
    return files


def _read_layout(reader: SummaryReader) -> _Case:
    dims = reader.dimensions
    if dims is None:
        raise InvalidSummaryError("Keyword DIMENS missing in summary spec")

    keys: list[str | None] = []
    by_key: dict[str, int] = {}
    rates: list[bool] = []
    keywords = list(reader.summary_keywords)
    key_types: dict[str, SummaryKeyType] = {}
    for i, kw in enumerate(keywords):
        variable = kw.summary_variable
        key_type = key_types.get(variable)
        if key_type is None:
            key_type = key_types[variable] = SummaryKeyType.from_variable(variable)
        # Most parameters are typically unused well/group slots, which
        # are skipped up front as raising for each of them is expensive
        if (key_type is _WELL or key_type is _GROUP) and (
            not kw.name or kw.name == _DUMMY_NAME
        ):
            keys.append(None)
            rates.append(False)
            continue
        try:
            key: str | None = make_summary_key(
                variable,
                kw.number,
                kw.name,
                dims[0],
                dims[1],
                kw.lgr_name,
                kw.li,
                kw.lj,
                kw.lk,
            )
        except InvalidSummaryKeyError:
            key = None
        keys.append(key)
        rates.append(key is not None and is_rate(variable))
        if key is not None:
            by_key[key] = i

    time_params = [i for i, kw in enumerate(keywords) if kw.summary_variable == "TIME"]
    if not time_params:
        raise InvalidSummaryError("KEYWORDS did not contain TIME in summary spec")
    time_param = time_params[-1]
    unit = keywords[time_param].unit
    if unit not in _SECONDS_PER_UNIT:
        raise InvalidSummaryError(f"Unknown date unit in summary spec: {unit}")

    return _Case(
        reader,
        keys,
        by_key,
        keywords,
        rates,
        time_param,
        _SECONDS_PER_UNIT[unit],
        reader.restart,
    )


def _pattern_index(case: _Case) -> dict[str, int]:
    """The last parameter index for each key that can be matched by a pattern.

    This is by_key, but also including alternative keys (using the number
    instead of the cell index or region pair) for block, completion and
    inter region keys, which can be matched by patterns but are not column names.
    """
    by_pattern: dict[str, int] = {}
    for i, (key, kw) in enumerate(zip(case.keys, case.keywords, strict=True)):
        if key is None:
            continue
        by_pattern[key] = i
        if kw.number is not None:
            match SummaryKeyType.from_variable(kw.summary_variable):
                case SummaryKeyType.BLOCK | SummaryKeyType.INTER_REGION:
                    by_pattern[f"{kw.summary_variable}:{kw.number}"] = i
                case SummaryKeyType.COMPLETION if kw.name:
                    by_pattern[f"{kw.summary_variable}:{kw.name}:{kw.number}"] = i
    return by_pattern


def _select_columns(
    first: _Case, column_keys: Sequence[str] | None
) -> list[tuple[str, int]]:
    """The names and parameter indices of the columns to include in the frame.

    No column keys means all, in the order of the file, otherwise
    each pattern gives the matching keys in natural sorted order.
    The last parameter with a given key is the one that is used, so
    duplicated keys give several columns with the same values.
    """
    if column_keys is None:
        return [(k, first.by_key[k]) for k in first.keys if k and k != "TIME"]
    by_pattern = _pattern_index(first)
    return [
        (key, by_pattern[key])
        for pattern in column_keys
        for key in natsorted(
            k
            for k in by_pattern
            if fnmatch.fnmatchcase(k, pattern)
            and not (k == "TIME" and pattern in ("*", ""))
        )
    ]


def _interpolate(
    times: npt.NDArray[np.int64],
    values: npt.NDArray[np.float64],
    rates: npt.NDArray[np.bool_],
    requested: npt.NDArray[np.int64],
) -> npt.NDArray[np.float64]:
    """Evaluate the values at the requested times.

    Rates are step functions, other values are interpolated. Outside the
    simulated range rates are 0 and others are the first/last value.
    """
    if len(times) == 0:
        return np.zeros((len(requested), values.shape[1]))
    after = np.searchsorted(times, requested, side="left")
    lower = np.maximum(after - 1, 0)
    upper = np.minimum(after, len(times) - 1)
    diff = (times[upper] - times[lower]).astype(np.float64)[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        weight_lower = -(requested - times[upper]).astype(np.float64)[:, None] / diff
        weight_upper = (requested - times[lower]).astype(np.float64)[:, None] / diff
        interpolated = np.where(
            (after == 0)[:, None],
            values[0],
            values[lower] * weight_lower + values[upper] * weight_upper,
        )
    inside = np.where(rates, values[upper], interpolated)
    below = (requested < times[0])[:, None]
    outside = np.where(rates, 0.0, np.where(below, values[0], values[-1]))
    return np.where(below | (requested > times[-1])[:, None], outside, inside)


def _open_reader(case: str) -> SummaryReader:
    """Open a SummaryReader for the given case.

    If the case is a directory (ends with a path separator) the base is the
    single ``.DATA`` file in the directory, otherwise file selection is
    left to SummaryReader.

    Raises:
        FileNotFoundError: If no matching summary files were found.
    """
    path, filename = os.path.split(case)
    if not filename:
        data_files = [
            f
            for f in Path(path or ".").iterdir()
            if f.is_file() and f.suffix in {".data", ".DATA"}
        ]
        if len(data_files) != 1:
            raise FileNotFoundError(f"Could not find any summary files matching {case}")
        case = str(Path(path) / data_files[0].stem)
    return SummaryReader(case_path=case)
