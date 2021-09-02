import datetime

import pandas as pd
import pytest

from ecl2df import EclFiles, compdat

try:
    import opm  # noqa
except ImportError:
    pytest.skip(
        "OPM is not installed",
        allow_module_level=True,
    )


@pytest.mark.parametrize(
    "deckstr, expected_df",
    [
        (
            """
    DATES
     1 MAY 2001 /
    /

    WLIST
     '*OP' NEW OP1 /
    /
    """,
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    }
                ]
            ),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            # Test initialization of list with no wells
            """
    DATES
     1 MAY 2001 /
    /

    WLIST
     '*OP' NEW /
    /
    """,
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "",
                        "DATE": datetime.date(2001, 5, 1),
                    }
                ]
            ),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            """
    DATES
     1 MAY 2001 /
    /

    WLIST
     '*OP' NEW OP1 /
    /

    DATES
     2 MAY 2001 /
    /
    WLIST
      '*OP' ADD OP2 OP3 /
    /
    """,
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                    {
                        "NAME": "OP",
                        "ACTION": "ADD",
                        "WELLS": "OP2 OP3",
                        "DATE": datetime.date(2001, 5, 2),
                    },
                ]
            ),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        # Construct well list from existing well list
        (
            """
    DATES
     1 MAY 2001 /
    /

    WLIST
     '*OP' NEW OP1 /
    /

    DATES
     2 MAY 2001 /
    /
    WLIST
      '*OPS' NEW /
      '*OPS' ADD '*OP' /
    /
    """,
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                    {
                        "NAME": "OPS",
                        "ACTION": "NEW",
                        "WELLS": "",
                        "DATE": datetime.date(2001, 5, 2),
                    },
                    {
                        "NAME": "OPS",
                        "ACTION": "ADD",
                        "WELLS": "*OP",
                        "DATE": datetime.date(2001, 5, 2),
                    },
                ]
            ),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
    ],
)
def test_parse_wlist(deckstr, expected_df):
    deck = EclFiles.str2deck(deckstr)
    wlistdf = compdat.deck2dfs(deck)["WLIST"]
    pd.testing.assert_frame_equal(wlistdf, expected_df, check_like=True)


@pytest.mark.parametrize(
    "wlist_df, expected_df",
    [
        pytest.param(
            pd.DataFrame([{}]),
            pd.DataFrame([{}]),
            # marks=pytest.mark.xfail(raises=KeyError),
        ),
        (
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP2 OP1",
                        "DATE": datetime.date(1900, 1, 1),
                    }
                ]
            ),
            # Only change is that well names are sorted:
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1 OP2",
                        "DATE": datetime.date(1900, 1, 1),
                    }
                ]
            ),
        ),
        (
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OP",
                        "ACTION": "ADD",
                        "WELLS": "OP2",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1 OP2",
                        "DATE": datetime.date(1900, 1, 1),
                    }
                ]
            ),
        ),
        (
            # Same as above, but split on two dates:
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OP",
                        "ACTION": "ADD",
                        "WELLS": "OP2",
                        "DATE": datetime.date(1900, 1, 2),
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1 OP2",
                        "DATE": datetime.date(1900, 1, 2),
                    },
                ]
            ),
        ),
        (
            # Existing well-lists will be repeated on subsequent dates:
            pd.DataFrame(
                [
                    {
                        "NAME": "OPA",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OPB",
                        "ACTION": "NEW",
                        "WELLS": "OP2",
                        "DATE": datetime.date(1900, 1, 2),
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "NAME": "OPA",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OPA",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(1900, 1, 2),
                    },
                    {
                        "NAME": "OPB",
                        "ACTION": "NEW",
                        "WELLS": "OP2",
                        "DATE": datetime.date(1900, 1, 2),
                    },
                ]
            ),
        ),
        (
            # Subsequent NEW statements with empty list clears existing
            # wells from the well list, here on the same date:
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                ]
            ),
        ),
        (
            # Subsequent NEW statements with empty list clears existing
            # wells from the well list:
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "",
                        "DATE": datetime.date(1900, 1, 2),
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "",
                        "DATE": datetime.date(1900, 1, 2),
                    },
                ]
            ),
        ),
        (
            pd.DataFrame(
                [
                    {
                        "NAME": "OPW",
                        "ACTION": "NEW",
                        "WELLS": "OP1 OP2",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OPE",
                        "ACTION": "NEW",
                        "WELLS": "OP3 OP4",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OPC",
                        "ACTION": "MOV",
                        "WELLS": "OP2 OP3",
                        "DATE": datetime.date(1900, 1, 2),
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "NAME": "OPW",
                        "ACTION": "NEW",
                        "WELLS": "OP1 OP2",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OPE",
                        "ACTION": "NEW",
                        "WELLS": "OP3 OP4",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OPW",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(1900, 1, 2),
                    },
                    {
                        "NAME": "OPE",
                        "ACTION": "NEW",
                        "WELLS": "OP4",
                        "DATE": datetime.date(1900, 1, 2),
                    },
                    {
                        "NAME": "OPC",
                        "ACTION": "NEW",
                        "WELLS": "OP2 OP3",
                        "DATE": datetime.date(1900, 1, 2),
                    },
                ]
            ),
        ),
        (
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1 OP2 OP3",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OP",
                        "ACTION": "DEL",
                        "WELLS": "OP2",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1 OP3",
                        "DATE": datetime.date(1900, 1, 1),
                    }
                ]
            ),
        ),
        (
            # Adding elements from another well list, defined
            # on the same date:
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                    {
                        "NAME": "OPS",
                        "ACTION": "NEW",
                        "WELLS": "",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                    {
                        "NAME": "OPS",
                        "ACTION": "ADD",
                        "WELLS": "*OP",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                    {
                        "NAME": "OPS",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                ]
            ),
        ),
        (
            # Adding elements from another well list,
            # directly with a NEW statement:
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                    {
                        "NAME": "OPS",
                        "ACTION": "NEW",
                        "WELLS": "*OP",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                    {
                        "NAME": "OPS",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                ]
            ),
        ),
        (
            # Adding elements from another well list,
            # directly with a NEW statement, recursively:
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                    {
                        "NAME": "OPS",
                        "ACTION": "NEW",
                        "WELLS": "*OP",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                    {
                        "NAME": "OPST",
                        "ACTION": "NEW",
                        "WELLS": "*OPS",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                    {
                        "NAME": "OPS",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                    {
                        "NAME": "OPST",
                        "ACTION": "NEW",
                        "WELLS": "OP1",
                        "DATE": datetime.date(2001, 5, 1),
                    },
                ]
            ),
        ),
        pytest.param(
            # Adding to a nonexisting list
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "ADD",
                        "WELLS": "OP1",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                ]
            ),
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            # Adding from a previously undefined list
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                    {
                        "NAME": "OP",
                        "ACTION": "ADD",
                        "WELLS": "*OPS",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                ]
            ),
            None,
            marks=pytest.mark.xfail(raises=ValueError),
            # "Recursive well list OPS does not exist"
        ),
        # Wildcard wells should pass through, the dataframe user
        # will have to process it.
        (
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "PROD*",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                ]
            ),
            pd.DataFrame(
                [
                    {
                        "NAME": "OP",
                        "ACTION": "NEW",
                        "WELLS": "PROD*",
                        "DATE": datetime.date(1900, 1, 1),
                    },
                ]
            ),
        ),
    ],
)
def test_expand_wlist(wlist_df, expected_df):
    pd.testing.assert_frame_equal(
        compdat.expand_wlist(wlist_df), expected_df, check_like=True
    )
