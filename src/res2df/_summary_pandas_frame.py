"""Read summary files into a pandas frame.

A "keyword index" is the index of a keyword in the ``KEYWORDS`` array of the
summary spec, which is also the index of its value in the ``PARAMS`` array of
each step in the summary data file.
"""

import fnmatch
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cached_property
from itertools import pairwise
from pathlib import Path
from typing import Any, Self

import numpy as np
import numpy.typing as npt
import pandas as pd
from natsort import natsorted
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
_DUMMY_NAME = ":+:+:+:+"
_CHUNK_BYTES = 64 * 1024 * 1024
_WELL = SummaryKeyType.WELL
_GROUP = SummaryKeyType.GROUP
_TOTAL_ROOTS = (
    "OPT", "OIT", "OVPT", "OVIT", "OMT", "GPT", "GIT", "GVPT", "GVIT", "GMT",
    "WGPT", "WGIT", "WPT", "WIT", "WVPT", "WVIT", "WMT", "LPT", "VPT", "VIT",
    "RGT", "EGT", "EXGT", "SGT", "GST", "FGT", "GIMT", "GCT", "NPT", "NIT",
    "CPT", "CIT", "SIT", "SPT", "TIT", "TPT", "GMIT",
)  # fmt: skip
_SEGMENT_TOTAL_ROOTS = ("OFT", "GFT", "WFT")
_LGR_TYPES = {
    SummaryKeyType.LOCAL_WELL,
    SummaryKeyType.LOCAL_BLOCK,
    SummaryKeyType.LOCAL_COMPLETION,
}
_WGNAME_TYPES = {
    SummaryKeyType.WELL,
    SummaryKeyType.GROUP,
    SummaryKeyType.COMPLETION,
    SummaryKeyType.SEGMENT,
    SummaryKeyType.LOCAL_WELL,
    SummaryKeyType.LOCAL_COMPLETION,
    SummaryKeyType.NETWORK,
}


def summary_pandas_frame(
    case: str | os.PathLike[str],
    time_index: str | date | Sequence[datetime | date] | None = None,
    column_keys: Sequence[str] | None = None,
    include_restart: bool = True,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> pd.DataFrame:
    """Create a pandas frame with summary data.

    One row for each time point (including ministeps), or the values
    interpolated to ``time_index`` if given. Rates are given as step functions
    (0 outside the simulated range) while other values are linearly
    interpolated (and constant outside the simulated range).

    The metadata (see :func:`res2df.summary.smry_meta`) for the
    columns is available as ``dframe.attrs["meta"]``.

    Args:
        case: The name of a summary case. The case can be the basename
            (``path/to/CASE``), a summary file (``path/to/CASE.UNSMRY``).
        time_index: Times to interpolate to, or a resampling frequency
            as accepted by :func:`res2df.summary.resample_smry_dates`.
            Default is the times in the summary.
        column_keys: List of key patterns (wildcards ``*`` etc. allowed),
            default is all summary vectors.
        include_restart: Whether to include data from the case it was restarted
            from.
        start_date: Passed on to :func:`res2df.summary.resample_smry_dates`
            when ``time_index`` is a string.
        end_date: Passed on to :func:`res2df.summary.resample_smry_dates`
            when ``time_index`` is a string.

    Raises:
        FileNotFoundError: If no summary files were found for the given case.
        InvalidSummaryError: If the summary files have invalid contents.
    """
    cases = _read_restart_chain(os.fspath(case), include_restart)
    main = cases[0]
    chosen = _select_columns(main, column_keys)
    columns = [name for name, _ in chosen]
    selected = [i for _, i in chosen]
    rates = np.array(
        [is_rate(main.keywords[i].summary_variable) for i in selected], dtype=bool
    )
    times, values = _merge([_read_block(c, chosen) for c in cases], len(selected))
    index: pd.Index
    if time_index is None:
        index = _seconds_index(times)
    elif isinstance(time_index, str) and time_index == "raw":
        times, values = _crop(times, values, rates, start_date, end_date)
        index = _seconds_index(times)
    else:
        index, requested = _requested(times, time_index, start_date, end_date)
        values = _interpolate(times, values, rates, requested)
    dframe = pd.DataFrame(index=index, columns=columns, data=values, copy=False)
    dframe.attrs["meta"] = {
        name: _meta(main.keywords[i]) for name, i in chosen if name != "TIME"
    }
    return dframe


def _seconds_index(times: npt.NDArray[np.int64]) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(times.astype("datetime64[s]")).as_unit("us")


def _requested(
    times: npt.NDArray[np.int64],
    time_index: str | date | Sequence[datetime | date],
    start_date: str | date | None,
    end_date: str | date | None,
) -> tuple[pd.Index, npt.NDArray[np.int64]]:
    """The index of the frame and the corresponding seconds to interpolate to."""
    index_values: Sequence[datetime | date]
    if isinstance(time_index, (str, date)):
        # Imported here as summary imports this module
        from .summary import resample_smry_dates  # noqa: PLC0415

        if len(times) == 0:
            return pd.Index([]), np.zeros(0, dtype=np.int64)
        # Resampling only depends on the first and last time
        index_values = resample_smry_dates(
            [_to_datetime(times.min()), _to_datetime(times.max())],
            time_index,  # type: ignore[arg-type]
            True,
            start_date,
            end_date,
        )
    else:
        index_values = list(time_index)
    requested = np.array([_naive_seconds(t) for t in index_values], dtype=np.int64)
    if index_values and all(
        isinstance(t, datetime) and t.tzinfo is None for t in index_values
    ):
        # pandas 2 would infer nanoseconds, which overflows after year 2262
        return pd.DatetimeIndex(
            np.array(index_values, dtype="datetime64[us]")
        ), requested
    return pd.Index(index_values), requested


def _crop(
    times: npt.NDArray[np.int64],
    values: npt.NDArray[np.float64],
    rates: npt.NDArray[np.bool_],
    start_date: str | date | None,
    end_date: str | date | None,
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]:
    """The times and values at resample_smry_dates(dates, "raw", ...).

    Equivalent to interpolating to those times, but the rows within the range
    are taken as is, and only the rows at start_date and end_date are
    interpolated.
    """
    from .summary import _ensure_date_or_none  # noqa: PLC0415

    if not np.all(times[1:] >= times[:-1]):
        order = np.argsort(times, kind="stable")
        times, values = times[order], values[order]
    start = _ensure_date_or_none(start_date)
    end = _ensure_date_or_none(end_date)
    if not start and not end:
        return times, values
    first, last = 0, len(times)
    head: list[int] = []
    tail: list[int] = []
    if start:
        head = [_naive_seconds(start)]
        first = int(np.searchsorted(times, head[0], "right"))
    if end:
        tail = [_naive_seconds(end)]
        last = int(np.searchsorted(times, tail[0], "left"))
    if head and tail and head[0] >= tail[0]:
        head = []  # The start is also cropped by the end
    edge_times = np.array(head + tail, dtype=np.int64)
    edge_values = _interpolate(times, values, rates, edge_times)
    inside = slice(first, max(first, last))
    return (
        np.concatenate(
            (edge_times[: len(head)], times[inside], edge_times[len(head) :])
        ),
        np.concatenate(
            (edge_values[: len(head)], values[inside], edge_values[len(head) :])
        ),
    )


def _to_datetime(seconds: np.int64) -> datetime:
    return _EPOCH + timedelta(seconds=int(seconds))


def _meta(kw: SummaryKeyword) -> dict[str, Any]:
    """Metadata for a summary vector, as given by resdata.summary.Summary"""
    variable = kw.summary_variable
    key_type = SummaryKeyType.from_variable(variable)
    meta: dict[str, Any] = {
        "unit": kw.unit,
        "is_total": _is_total(variable, key_type),
        "is_rate": is_rate(variable),
        "is_historical": variable.endswith("H")
        and key_type in (_WELL, _GROUP, SummaryKeyType.FIELD),
        "keyword": variable,
        "wgname": kw.name
        if key_type in _WGNAME_TYPES and kw.name and kw.name != _DUMMY_NAME
        else None,
    }
    if key_type in _LGR_TYPES:
        meta["get_num"] = 0  # resdata does not use NUMS for LGR variables
    elif kw.number is not None:
        meta["get_num"] = int(kw.number)
    return meta


def _is_total(variable: str, key_type: SummaryKeyType) -> bool:
    match key_type:
        case (
            SummaryKeyType.WELL
            | SummaryKeyType.GROUP
            | SummaryKeyType.FIELD
            | SummaryKeyType.REGION
            | SummaryKeyType.COMPLETION
        ):
            return variable[1:].startswith(_TOTAL_ROOTS)
        case SummaryKeyType.LOCAL_WELL | SummaryKeyType.LOCAL_COMPLETION:
            return variable[2:].startswith(_TOTAL_ROOTS)
        case SummaryKeyType.SEGMENT:
            return variable[1:].startswith(_SEGMENT_TOTAL_ROOTS)
        case SummaryKeyType.INTER_REGION:
            return variable[2:4] == "FT" or variable[3:5] == "FT"
        case _:
            return False


def summary_meta(case: str | os.PathLike[str]) -> dict[str, dict[str, Any]]:
    """Metadata for all the summary vectors of the case.

    See :func:`res2df.summary.smry_meta` for the content.
    """
    main = _KeyedReader.read(SummaryReader(case_path=os.fspath(case)))
    return {
        key: _meta(main.keywords[i]) for key, i in main.by_key.items() if key != "TIME"
    }


def _naive_seconds(time: datetime | date) -> int:
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


@dataclass(frozen=True)
class _KeyedReader:
    """The layout of one summary (its keys) and the reader.

    Attributes:
        reader: Reader for the summary files of the case.
        keywords: The keyword (variable, name, number, ...) at each keyword index.
        dimensions: The first two values of DIMENS in the summary spec.
        time_keyword_index: The keyword index of TIME.
        time_unit: The number of seconds per unit of TIME.
        restart: Path of the case this case was restarted from.
        keys: The summary key at each keyword index, None if invalid.
        by_key: The last keyword index for each key.
    """

    reader: SummaryReader
    keywords: tuple[SummaryKeyword, ...]
    dimensions: tuple[int, int]
    time_keyword_index: int
    time_unit: int
    restart: str | None

    @cached_property
    def keys(self) -> list[str | None]:
        keys: list[str | None] = []
        key_types: dict[str, SummaryKeyType] = {}
        for kw in self.keywords:
            variable = kw.summary_variable
            key_type = key_types.get(variable)
            if key_type is None:
                key_type = key_types[variable] = SummaryKeyType.from_variable(variable)
            # Most keyword indices are typically unused well/group slots, which
            # are skipped up front as raising for each of them is expensive
            if (key_type is _WELL or key_type is _GROUP) and (
                not kw.name or kw.name == _DUMMY_NAME
            ):
                keys.append(None)
                continue
            try:
                keys.append(
                    make_summary_key(
                        variable,
                        kw.number,
                        kw.name,
                        self.dimensions[0],
                        self.dimensions[1],
                        kw.lgr_name,
                        kw.li,
                        kw.lj,
                        kw.lk,
                    )
                )
            except InvalidSummaryKeyError:
                keys.append(None)
        return keys

    @cached_property
    def by_key(self) -> dict[str, int]:
        return {key: i for i, key in enumerate(self.keys) if key is not None}

    @classmethod
    def read(cls, reader: SummaryReader) -> Self:
        dims = reader.dimensions
        if dims is None:
            raise InvalidSummaryError("Keyword DIMENS missing in summary spec")
        keywords = tuple(reader.summary_keywords)

        time_keyword_indices = [
            i for i, kw in enumerate(keywords) if kw.summary_variable == "TIME"
        ]
        if not time_keyword_indices:
            raise InvalidSummaryError("KEYWORDS did not contain TIME in summary spec")
        time_keyword_index = time_keyword_indices[-1]
        unit = keywords[time_keyword_index].unit
        if unit not in _SECONDS_PER_UNIT:
            raise InvalidSummaryError(f"Unknown date unit in summary spec: {unit}")

        return cls(
            reader,
            keywords,
            (dims[0], dims[1]),
            time_keyword_index,
            _SECONDS_PER_UNIT[unit],
            reader.restart,
        )


def _read_block(
    case: _KeyedReader, chosen: list[tuple[str, int]]
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]:
    """The times and values for the chosen columns, found by key in the case.

    Only the needed keyword indices are kept while reading. Columns
    not present in the case gets the default value.
    """
    source = [case.by_key.get(name) for name, _ in chosen]
    found = [i for i, src in enumerate(source) if src is not None]
    times, values = _read_values(case, [src for src in source if src is not None])
    if len(found) == len(chosen):
        return times, values
    block = np.full((len(times), len(chosen)), _DEFAULT_VALUE)
    block[:, found] = values
    return times, block


def _read_values(
    case: _KeyedReader, keyword_indices: list[int]
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]:
    """The time (in seconds since epoch) and values for each step."""
    columns = np.array([case.time_keyword_index, *keyword_indices], dtype=np.intp)
    data = np.empty((256, len(columns)), dtype=np.float32)
    steps = 0
    for row in case.reader.values(report_step_only=False):
        if len(row) != len(case.keywords):
            raise InvalidSummaryError(
                f"Expected {len(case.keywords)} values in each step, got {len(row)}"
            )
        if steps == len(data):
            data.resize((2 * steps, len(columns)), refcheck=False)
        data[steps] = row[columns]
        steps += 1
    data = data[:steps]
    # resdata ignores the time of day in STARTDAT
    # one can avoid this by dropping .date()
    # kept for backwards compatability
    start_time = _naive_seconds(case.reader.start_date.date())
    times = np.trunc(start_time + data[:, 0].astype(np.float64) * case.time_unit)
    return times.astype(np.int64), data[:, 1:].astype(np.float64)


def _merge(
    blocks: list[tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]], width: int
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]:
    """Merge the times and values of the cases (the first being the main case).

    The cases are ordered by their start, and each case is cut
    where the next one starts.
    """

    # When the main case and a restart ancestor share their first timestamp,
    # the following cutoff discards all the main cases rows. For example, main
    # times [0, 10, 20] and parent times [0, 10] produce only the parent's
    # data, losing the main-case timestep. This is a known quirk, and is kept
    # like this for backwards compatability with resdata.Summary.pandas_frame

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
        return parts[0]  # Avoid creating a copy with np.concatenate
    return np.concatenate([t for t, _ in parts]), np.concatenate([v for _, v in parts])


def _read_restart_chain(case_path: str, include_restart: bool) -> list[_KeyedReader]:
    files: list[_KeyedReader] = []
    visited: set[Path] = set()
    current: str | None = case_path
    while current and Path(current).resolve() not in visited:
        try:
            reader = SummaryReader(case_path=current)
        except FileNotFoundError:
            if not files:  # No files found
                raise
            else:
                break  # Did not find a restart
        files.append(_KeyedReader.read(reader))
        visited.add(Path(current).resolve())
        current = files[-1].restart if include_restart else None
    return files


def _select_columns(
    first: _KeyedReader, column_keys: Sequence[str] | None
) -> list[tuple[str, int]]:
    """The names and keyword indices of the columns to include in the frame.

    No column keys means all, in the order of the file, otherwise
    each pattern gives the matching keys in natural sorted order.
    The last keyword index with a given key is the one that is used, so
    duplicated keys give several columns with the same values.
    """
    if column_keys is None:
        return [(k, first.by_key[k]) for k in first.keys if k and k != "TIME"]
    if not column_keys:
        return []
    by_pattern = first.by_key
    wildcards = [p for p in column_keys if _is_wildcard(p)]
    # One pass with all patterns combined (as in resdata's view_summary),
    # the per-pattern matching then only visits the candidates.
    candidates: list[str] = []
    if wildcards:
        any_match = re.compile("|".join(map(fnmatch.translate, wildcards))).match
        candidates = [k for k in by_pattern if any_match(k)]
    chosen = []
    for pattern in column_keys:
        if not _is_wildcard(pattern):
            if pattern in by_pattern:
                chosen.append((pattern, by_pattern[pattern]))
            continue
        match = re.compile(fnmatch.translate(pattern)).match
        keys = [k for k in candidates if match(k)]
        if pattern == "*" and "TIME" in by_pattern:
            keys.remove("TIME")
        chosen.extend((key, by_pattern[key]) for key in natsorted(keys))
    return chosen


def _is_wildcard(pattern: str) -> bool:
    return any(c in pattern for c in "*?[")


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
    result = np.empty((len(requested), values.shape[1]))
    # Interpolate in chunks to bound the size of the temporaries
    rows = max(1, _CHUNK_BYTES // max(1, values.shape[1] * values.itemsize))
    for start in range(0, len(requested), rows):
        chunk = slice(start, start + rows)
        _interpolate_into(times, values, rates, requested[chunk], result[chunk])
    return result


def _interpolate_into(
    times: npt.NDArray[np.int64],
    values: npt.NDArray[np.float64],
    rates: npt.NDArray[np.bool_],
    requested: npt.NDArray[np.int64],
    result: npt.NDArray[np.float64],
) -> None:
    after = np.searchsorted(times, requested, side="left")
    lower = np.maximum(after - 1, 0)
    upper = np.minimum(after, len(times) - 1)
    diff = (times[upper] - times[lower]).astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        # Weights computed as in resdata to get the same rounding
        weight_lower = (times[upper] - requested) / diff
        weight_upper = (requested - times[lower]) / diff
    first = after == 0
    weight_lower[first] = 1.0
    weight_upper[first] = 0.0
    np.take(values, lower, axis=0, out=result)
    result *= weight_lower[:, None]
    result += values[upper] * weight_upper[:, None]
    if rates.any():
        result[:, rates] = values[upper][:, rates]
    below = requested < times[0]
    above = requested > times[-1]
    if below.any():
        result[below] = np.where(rates, 0.0, values[0])
    if above.any():
        result[above] = np.where(rates, 0.0, values[-1])
