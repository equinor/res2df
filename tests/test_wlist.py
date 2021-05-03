import datetime

import pandas as pd

import pytest

from ecl2df import compdat
from ecl2df import EclFiles


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
        # Wildcard wells are currently not supported
        # (it requires knowledge of all currenly processed wells)
        pytest.param(
            """
    WLIST
     '*OP' NEW 'PROD*' /
    /

    """,
            None,
            id="wellcardwlist",
            marks=pytest.mark.xfail(
                raises=NotImplementedError, match="Wildcards in WLIST are not supported"
            ),
        ),
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
    ],
)
def test_expand_wlist(wlist_df, expected_df):
    pd.testing.assert_frame_equal(
        compdat.expand_wlist(wlist_df), expected_df, check_like=True
    )
