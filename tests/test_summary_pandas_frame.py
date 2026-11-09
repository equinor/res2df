import dataclasses
import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
import resfo
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from resdata.summary import Summary
from resfo_utilities import SummaryKeyType, history_key
from resfo_utilities.testing import (
    Date,
    Simulator,
    Smspec,
    SmspecIntehead,
    SummaryMiniStep,
    SummaryStep,
    UnitSystem,
    Unsmry,
    summaries,
)

from res2df import ResdataFiles
from res2df._summary_pandas_frame import (
    _KeyedReader,
    _read_restart_chain,
    summary_pandas_frame,
)
from res2df.summary import df

pytestmark = pytest.mark.filterwarnings("ignore")

fast_settings = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=list(HealthCheck),
)


def write_case(
    directory: Path,
    name: str,
    smspec: Smspec,
    unsmry: Unsmry,
    formatted: bool = False,
    unified: bool = True,
) -> None:
    fmt = resfo.Format.FORMATTED if formatted else resfo.Format.UNFORMATTED
    prefix = "F" if formatted else ""
    smspec.to_file(directory / f"{name}.{prefix}SMSPEC", file_format=fmt)
    if unified:
        unsmry.to_file(directory / f"{name}.{prefix}UNSMRY", file_format=fmt)
    else:
        leading = "A" if formatted else "S"
        for i, step in enumerate(unsmry.steps):
            resfo.write(directory / f"{name}.{leading}{i + 1:04d}", step.to_smry(), fmt)


def load_summary(case: str, **kwargs) -> Summary:
    # lazy loading of formatted summaries is broken in resdata 6.3.5
    return Summary(case, lazy_load=False, **kwargs)


# In the following we, just say "equivalent" to mean that summary.df
# returns the same value when given a ResdataFiles (using
# summary_pandas_frame) as when given the reference resdata Summary
# object (using Summary.pandas_frame)


def _pattern_index(case: _KeyedReader) -> dict[str, int]:
    """The last parameter index for each key that can be matched by a pattern."""
    by_pattern: dict[str, int] = {}
    for i, (key, kw) in enumerate(zip(case.keys, case.keywords, strict=True)):
        if key is None:
            continue
        by_pattern[key] = i
        # Also match on the alternate "key2" used by resdata
        if kw.number is not None:
            match SummaryKeyType.from_variable(kw.summary_variable):
                case SummaryKeyType.BLOCK | SummaryKeyType.INTER_REGION:
                    by_pattern[f"{kw.summary_variable}:{kw.number}"] = i
                case SummaryKeyType.COMPLETION if kw.name:
                    by_pattern[f"{kw.summary_variable}:{kw.name}:{kw.number}"] = i
    return by_pattern


def _drop_key2_columns(
    expected: pd.DataFrame, case: str, include_restart: bool
) -> pd.DataFrame:
    """Drop columns only available through the alternate "key2" used by resdata."""
    key2s: set[str] = set()
    real: set[str] = set()
    for c in _read_restart_chain(case, include_restart):
        real.update(k for k in c.keys if k is not None)
        key2s.update(_pattern_index(c))
    drop = key2s - real
    meta = expected.attrs.get("meta")
    expected = expected.drop(columns=[c for c in expected.columns if c in drop])
    if meta is not None:
        expected.attrs["meta"] = {k: v for k, v in meta.items() if k not in drop}
    return expected


def reference(case: str, time_index=None, column_keys=None, include_restart=True, **kw):
    summary = load_summary(case, include_restart=include_restart)
    return _drop_key2_columns(
        df(summary, time_index, column_keys, **kw), case, include_restart
    )


def actual(case: str, time_index=None, column_keys=None, include_restart=True, **kw):
    return df(
        ResdataFiles(case),
        time_index,
        column_keys,
        include_restart=include_restart,
        **kw,
    )


def _comparable_attrs(attrs: dict) -> dict:
    # resdata <= 6.3.x reports the LGR name as wgname for local block vectors
    # (LB*), while resdata >= 7.0.0-b3 (resdata commit 14c576fce) reports None.
    meta = {
        key: {**value, "wgname": None} if key.startswith("LB") else value
        for key, value in attrs.get("meta", {}).items()
    }
    return {**attrs, "meta": meta}


def assert_equivalent(
    case: str, time_index=None, column_keys=None, include_restart=True, **kw
) -> pd.DataFrame | None:
    try:
        expected = reference(case, time_index, column_keys, include_restart, **kw)
    except ValueError as err:
        # Duplicate timestamps without a TIMESTEP vector
        with pytest.raises(ValueError, match=re.escape(str(err))):
            actual(case, time_index, column_keys, include_restart, **kw)
        return None
    frame = actual(case, time_index, column_keys, include_restart, **kw)
    pd.testing.assert_frame_equal(frame, expected, check_exact=True)
    assert _comparable_attrs(frame.attrs) == _comparable_attrs(expected.attrs)
    return frame


def time_indices(smry: Summary) -> list[list[datetime]]:
    dates = smry.dates
    first, last = dates[0], dates[-1]
    mid = [first + (last - first) * f / 7 for f in range(8)]
    return [
        [first - timedelta(days=3), *mid, last + timedelta(days=3)],
        dates[::2],
        [last],
    ]


def tmp_case(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("case")


@pytest.fixture
def workdir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("case")


@pytest.fixture
def make_dir(tmp_path_factory):
    return lambda: tmp_path_factory.mktemp("case")


@fast_settings
@given(summaries(), st.booleans(), st.booleans())
def test_that_all_columns_and_times_are_equivalent(
    make_dir, generated, formatted, unified
):
    smspec, unsmry = generated
    directory = make_dir()
    write_case(directory, "CASE", smspec, unsmry, formatted, unified)
    case = str(directory / "CASE")
    assert_equivalent(case)
    for time_index in time_indices(load_summary(case)):
        assert_equivalent(case, time_index)


@fast_settings
@given(summaries(), st.booleans())
def test_that_patterns_are_equivalent(make_dir, generated, formatted):
    smspec, unsmry = generated
    directory = make_dir()
    write_case(directory, "CASE", smspec, unsmry, formatted)
    case = str(directory / "CASE")
    keys = list(smspec.summary_keys())
    for patterns in (
        ["*"],
        ["F*", "W*", "TIME"],
        ["*:*", "*"],
        ["NOTAKEY", keys[0] if keys else "X"],
        [k[:2] + "*" for k in keys[:3]],
        [history_key(k) for k in keys[:3]],
        [],
    ):
        assert_equivalent(case, None, patterns)
        assert_equivalent(case, time_indices(load_summary(case))[0], patterns)


@fast_settings
@given(generated=summaries(), formatted=st.booleans(), unified=st.booleans())
def test_that_summary_files_can_be_given_by_extension(
    make_dir, generated, formatted, unified
):
    smspec, unsmry = generated
    directory = make_dir()
    write_case(directory, "CASE", smspec, unsmry, formatted, unified)
    prefix = "F" if formatted else ""
    candidates = [directory / "CASE", directory / "CASE.DATA"]
    if unified:
        candidates += [
            directory / f"CASE.{prefix}SMSPEC",
            directory / f"CASE.{prefix}UNSMRY",
        ]
    for candidate in candidates:
        try:
            load_summary(str(candidate))
        except OSError:
            # SummaryReader is more lenient than resdata about extensions
            continue
        assert_equivalent(str(candidate))


@fast_settings
@given(generated=summaries(), formatted=st.booleans())
def test_that_lower_case_files_are_equivalent(make_dir, generated, formatted):
    smspec, unsmry = generated
    directory = make_dir()
    write_case(directory, "CASE", smspec, unsmry, formatted)
    for path in list(directory.iterdir()):
        path.rename(path.with_name(path.name.lower()))
    for name in ("case", "case.smspec", "case.fsmspec", "case.unsmry"):
        case = str(directory / name)
        try:
            load_summary(case)
        except OSError:
            with pytest.raises(OSError):
                summary_pandas_frame(case)
        else:
            assert_equivalent(case)


@fast_settings
@given(
    first=summaries(),
    second=summaries(),
    formatted=st.booleans(),
    unified=st.booleans(),
    include_restart=st.booleans(),
    relative=st.booleans(),
)
def test_that_restart_cases_are_equivalent(
    make_dir, first, second, formatted, unified, include_restart, relative
):
    directory = make_dir()
    first_smspec, first_unsmry = first
    second_smspec, second_unsmry = second
    write_case(directory, "FIRST", first_smspec, first_unsmry, formatted, unified)
    restart = "FIRST" if relative else str(directory / "FIRST")
    assume(len(restart) <= 72)
    second_smspec = dataclasses.replace(second_smspec, restart=restart)
    write_case(directory, "SECOND", second_smspec, second_unsmry, formatted, unified)
    case = str(directory / "SECOND")
    assert_equivalent(case, include_restart=include_restart)
    assert_equivalent(case, None, ["F*", "*:*"], include_restart)
    for time_index in time_indices(load_summary(case, include_restart=include_restart)):
        assert_equivalent(case, time_index, None, include_restart)


@fast_settings
@given(summaries(), summaries(), summaries())
def test_that_chained_restarts_are_equivalent(make_dir, first, second, third):
    directory = make_dir()
    write_case(directory, "A", *first)
    write_case(directory, "B", dataclasses.replace(second[0], restart="A"), second[1])
    write_case(directory, "C", dataclasses.replace(third[0], restart="B"), third[1])
    assert_equivalent(str(directory / "C"))


def test_that_missing_restart_case_is_ignored(tmp_path):
    smspec, unsmry = summaries().example()
    write_case(tmp_path, "CASE", dataclasses.replace(smspec, restart="MISSING"), unsmry)
    assert_equivalent(str(tmp_path / "CASE"))


def cell_number(ijk: str) -> int:
    i, j, k = map(int, ijk.split(","))
    return i + (j - 1) * 2 + (k - 1) * 4


def parse_key(key: str) -> tuple[str, int, str]:
    """Returns the well name, number and lgr name used in the smspec for a key."""
    parts = key.split(":")
    name = ":+:+:+:+"
    number = 0
    lgr = ""
    if parts[0].startswith("L"):
        lgr = parts[1]
        parts = [parts[0], *parts[2:]]
    if len(parts) > 1:
        if parts[0] in ("RGFR", "ROFR"):
            r1, r2 = map(int, parts[1].split("-"))
            number = r1 + 32768 * (r2 + 10)
        elif parts[0][0] in "WGSC" and not parts[0].startswith("AA"):
            name = parts[1]
            if len(parts) > 2 and "," in parts[2]:
                number = cell_number(parts[2])
            elif len(parts) > 2:
                number = int(parts[2])
        elif parts[0][0] in "AR":
            number = int(parts[1])
        elif parts[0][0] == "B":
            number = cell_number(parts[1])
    return name, number, lgr


@pytest.mark.parametrize(
    "keys",
    [
        ["FOPR", "FOPT", "FOPRH", "FOPTH", "FWCT", "FGOR", "FPR", "FOIP"],
        ["WOPR:W1", "WWCT:W1", "WBHP:W1", "WOPRH:W1", "WOPR:W2"],
        ["GOPR:G1", "GWIR:G2", "GGOR:G1"],
        ["ROPR:1", "RPR:2", "RPR:10", "RPR:3", "RGPT:1"],
        ["BPR:1,1,1", "BPR:2,1,1", "BGSAT:1,2,1"],
        ["COPR:W1:1,1,1", "CWIR:W2:2,1,1"],
        ["LWOPR:LGR1:W1", "LBPR:LGR1:1,1,1", "LCOPR:LGR1:W1:1,1,1"],
        ["SOFR:W1:1", "SPR:W1:2"],
        ["AAQR:1", "ANQR:2"],
        ["RGFR:1-2", "ROFR:1-2"],
        ["NEWTON", "TCPU", "FOPRS"],
    ],
)
@pytest.mark.parametrize("use_days", [True, False])
def test_that_key_types_are_equivalent(tmp_path, keys, use_days):
    n = len(keys)
    times = [0.0, 1.5, 3.0, 4.0, 10.0]
    steps = [
        SummaryStep(
            seqnum=i,
            ministeps=[
                SummaryMiniStep(
                    mini_step=i,
                    params=[t, *[float(i * 7 + j + 1) / 3 for j in range(n)]],
                )
            ],
        )
        for i, t in enumerate(times)
    ]
    summary_keys = [k.split(":")[0] for k in keys]
    parsed = [parse_key(k) for k in keys]
    names = [name.ljust(8) for name, _, _ in parsed]
    numbers = [number for _, number, _ in parsed]
    lgrs = [lgr.ljust(8) for _, _, lgr in parsed]
    use_locals = any(k.startswith("L") for k in summary_keys)
    smspec = Smspec(
        nx=2,
        ny=2,
        nz=2,
        restarted_from_step=0,
        num_keywords=n + 1,
        restart="        ",
        keywords=["TIME    ", *[k.ljust(8) for k in summary_keys]],
        well_names=[":+:+:+:+", *names],
        region_numbers=[-32676, *numbers],
        units=["DAYS    " if use_days else "HOURS   ", *["SM3     "] * n],
        start_date=Date(day=1, month=1, year=2014, hour=0, minutes=0, micro_seconds=0),
        intehead=SmspecIntehead(
            unit=UnitSystem.METRIC, simulator=Simulator.ECLIPSE_100
        ),
        lgrs=["        ", *lgrs] if use_locals else None,
        numlx=[0, *[1] * n] if use_locals else None,
        numly=[0, *[1] * n] if use_locals else None,
        numlz=[0, *[1] * n] if use_locals else None,
    )
    write_case(tmp_path, "CASE", smspec, Unsmry(steps))
    case = str(tmp_path / "CASE")
    frame = assert_equivalent(case)
    assert frame is not None
    assert len(frame.columns) > 0
    smry = load_summary(case)
    for time_index in time_indices(smry):
        assert_equivalent(case, time_index)
    assert_equivalent(case, None, ["*"])
    assert_equivalent(case, None, ["*", "F*", "R*", "W*:*"])


def test_that_duplicate_keys_are_equivalent(tmp_path):
    steps = [
        SummaryStep(
            seqnum=i,
            ministeps=[
                SummaryMiniStep(mini_step=i, params=[float(i), 1.0 + i, 5.0 * i])
            ],
        )
        for i in range(3)
    ]
    smspec = Smspec(
        nx=2,
        ny=2,
        nz=2,
        restarted_from_step=0,
        num_keywords=3,
        restart="        ",
        keywords=["TIME    ", "FOPR    ", "FOPR    "],
        well_names=[":+:+:+:+"] * 3,
        region_numbers=[-32676, 0, 0],
        units=["DAYS    ", "SM3     ", "SM3     "],
        start_date=Date(day=1, month=1, year=2014, hour=0, minutes=0, micro_seconds=0),
        intehead=SmspecIntehead(
            unit=UnitSystem.METRIC, simulator=Simulator.ECLIPSE_100
        ),
    )
    write_case(tmp_path, "CASE", smspec, Unsmry(steps))
    case = str(tmp_path / "CASE")
    assert_equivalent(case)
    assert_equivalent(case, None, ["FOPR"])


def test_that_missing_case_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        summary_pandas_frame(str(tmp_path / "NOPE"))


POOL_KEYS = ["FOPR", "FOPT", "FGOR", "WOPR:A", "WOPR:B", "WBHP:A", "BPR:1,1,1", "RPR:1"]
pool_keys = st.lists(st.sampled_from(POOL_KEYS), unique=True, min_size=1).map(
    lambda keys: [k for k in POOL_KEYS if k in keys]
)
close_dates = st.integers(0, 30).map(lambda d: datetime(2000, 1, 1) + timedelta(days=d))
small_deltas = st.lists(st.floats(0.5, 40.0).map(lambda x: round(x, 1)), max_size=8)
overlapping = summaries(
    start_date=close_dates,
    time_deltas=small_deltas,
    summary_keys=pool_keys,
    use_days=st.just(True),
)


@fast_settings
@given(
    summaries(),
    st.lists(st.integers(-10_000_000, 400_000_000), max_size=12),
    st.integers(0, 999_999),
    st.booleans(),
    st.booleans(),
)
def test_that_arbitrary_time_indices_are_equivalent(
    make_dir, generated, offsets, microsecond, as_dates, sort
):
    smspec, unsmry = generated
    directory = make_dir()
    write_case(directory, "CASE", smspec, unsmry)
    case = str(directory / "CASE")
    first = load_summary(case).dates[0]
    time_index = [
        first + timedelta(seconds=s, microseconds=microsecond) for s in offsets
    ]
    if sort:
        time_index.sort()
    if as_dates:
        time_index = [t.date() for t in time_index]
    assert_equivalent(case, time_index)
    assert_equivalent(case, time_index, ["F*", "W*"])


@fast_settings
@given(
    generated=overlapping,
    time_index=st.sampled_from(["raw", "daily", "monthly", "yearly"]),
    start_date=st.one_of(st.none(), close_dates),
    end_date=st.one_of(st.none(), close_dates),
    small_chunks=st.booleans(),
)
def test_that_resampling_with_date_range_is_equivalent(
    make_dir, generated, time_index, start_date, end_date, small_chunks, monkeypatch
):
    smspec, unsmry = generated
    directory = make_dir()
    write_case(directory, "CASE", smspec, unsmry)
    case = str(directory / "CASE")
    assume(len(load_summary(case).dates) > 1)
    if small_chunks:  # Exercise the chunked interpolation
        monkeypatch.setattr("res2df._summary_pandas_frame._CHUNK_BYTES", 16)
    assert_equivalent(case, time_index, start_date=start_date, end_date=end_date)
    if end_date is not None:
        assert_equivalent(case, time_index, end_date=end_date.date())


@fast_settings
@given(summaries(time_deltas=st.just([])))
def test_that_case_with_one_time_is_equivalent(make_dir, generated):
    smspec, unsmry = generated
    directory = make_dir()
    write_case(directory, "CASE", smspec, unsmry)
    case = str(directory / "CASE")
    assert_equivalent(case)
    smry = load_summary(case)
    for time_index in time_indices(smry):
        assert_equivalent(case, time_index)


@fast_settings
@given(
    summaries(
        time_deltas=st.lists(st.sampled_from([0.0, 1.0, 1.0, 2.0, 2.0]), max_size=8)
    )
)
def test_that_repeated_times_are_equivalent(make_dir, generated):
    smspec, unsmry = generated
    directory = make_dir()
    write_case(directory, "CASE", smspec, unsmry)
    case = str(directory / "CASE")
    assert_equivalent(case)
    for time_index in time_indices(load_summary(case)):
        assert_equivalent(case, time_index)


@fast_settings
@given(summaries())
def test_that_case_without_steps_gives_empty_frame(make_dir, generated):
    # resdata refuses to open such a case, which summary.df turns into an
    # empty dataframe, so here we only require no rows.
    smspec, _ = generated
    directory = make_dir()
    write_case(directory, "CASE", smspec, Unsmry([]))
    assert len(summary_pandas_frame(str(directory / "CASE"))) == 0


@st.composite
def key_patterns(draw, keys: list[str]) -> list[str]:
    def pattern() -> str:
        key = draw(st.sampled_from(keys))
        cut = draw(st.integers(0, len(key)))
        return draw(
            st.sampled_from(
                [
                    key,
                    key[:cut] + "*",
                    "*" + key[cut:],
                    key[:cut] + "?" + key[cut + 1 :],
                    "[A-F]" + key[1:],
                    "*",
                    "",
                    "NOT*",
                ]
            )
        )

    return draw(st.lists(st.builds(pattern), max_size=5))


@fast_settings
@given(st.data(), summaries(), st.booleans())
def test_that_random_patterns_are_equivalent(make_dir, data, generated, use_time):
    smspec, unsmry = generated
    directory = make_dir()
    write_case(directory, "CASE", smspec, unsmry)
    case = str(directory / "CASE")
    patterns = data.draw(key_patterns(["TIME", *smspec.summary_keys()]))
    time_index = time_indices(load_summary(case))[0] if use_time else None
    assert_equivalent(case, time_index, patterns)


@fast_settings
@given(overlapping, overlapping, st.booleans())
def test_that_overlapping_restarts_with_different_keys_are_equivalent(
    make_dir, first, second, use_time
):
    directory = make_dir()
    write_case(directory, "FIRST", *first)
    write_case(
        directory, "SECOND", dataclasses.replace(second[0], restart="FIRST"), second[1]
    )
    case = str(directory / "SECOND")
    assert_equivalent(case)
    assert_equivalent(case, None, ["F*", "W*", "*:*"])
    if use_time:
        for time_index in time_indices(load_summary(case)):
            assert_equivalent(case, time_index)
