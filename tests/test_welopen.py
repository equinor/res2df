import datetime

import pandas as pd

import pytest

from ecl2df import compdat
from ecl2df import EclFiles

WELOPEN_CASES = [
    # Simplest possible WELOPEN case
    (
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
    ),
    # Test the defaults handling in WELOPEN:
    (
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' 5* /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
    ),
    # Test the defaults handling in WELOPEN (zero value means apply to all)
    (
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' 0 0 0 0 0 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
    ),
    # Test the defaults handling in WELOPEN (default values are negative)
    (
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' -1 -1 -1 -1 -1 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
    ),
    # Fail with ValueError when both I,J,K (3-5) and completions number (6-7)
    # are defined in WELOPEN
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     -- This also specifies lumped connections, which will give crash
     'OP1' 'SHUT' 1 1 1 1 1 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
        marks=pytest.mark.xfail(raises=ValueError),
    ),
    # Test J slicing
    (
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 3 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' 1 1 2  /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "OPEN"],
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 2, 2, "SHUT"],
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 3, 3, "OPEN"],
            ],
        ),
    ),
    # Test multiple connections to the same cell
    # (ecl2df <= 0.13.1 would remove OP1 from this dataframe)
    (
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
     'OP2' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT'  /
     'OP2' 'OPEN'  /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 1, 1), "OP2", 1, 1, 1, 1, "OPEN"],
            ],
        ),
    ),
    # Test multiple time steps
    (
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 33 110 31 31 'OPEN'  /
    /

    WELOPEN
     'OP1' 'SHUT' /
    /

    TSTEP
     1 /

    COMPDAT
     'OP1' 34 111 32 32 'OPEN' /
    /

    TSTEP
     2 3 /

    COMPDAT
     'OP1' 35 111 33 33 'SHUT' /
    /
    """,
        pd.DataFrame(
            {
                "WELL": {0: "OP1", 1: "OP1", 2: "OP1"},
                "I": {0: 33, 1: 34, 2: 35},
                "J": {0: 110, 1: 111, 2: 111},
                "K1": {0: 31, 1: 32, 2: 33},
                "K2": {0: 31, 1: 32, 2: 33},
                "OP/SH": {0: "SHUT", 1: "OPEN", 2: "SHUT"},
                "DATE": {
                    0: datetime.date(2001, 5, 1),
                    1: datetime.date(2001, 5, 2),
                    2: datetime.date(2001, 5, 7),
                },
            }
        ),
    ),
    (
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 33 110 31 31 'OPEN'  /
    /

    WELOPEN
     'OP1' 'OPEN' /
    /

    TSTEP
     1 /

    COMPDAT
     'OP1' 34 111 32 32 'OPEN' /
    /

    TSTEP
     2 3 /

    COMPDAT
     'OP1' 35 111 33 33 'SHUT' /
    /
    """,
        pd.DataFrame(
            {
                "WELL": {0: "OP1", 1: "OP1", 2: "OP1"},
                "I": {0: 33, 1: 34, 2: 35},
                "J": {0: 110, 1: 111, 2: 111},
                "K1": {0: 31, 1: 32, 2: 33},
                "K2": {0: 31, 1: 32, 2: 33},
                "OP/SH": {0: "OPEN", 1: "OPEN", 2: "SHUT"},
                "DATE": {
                    0: datetime.date(2001, 5, 1),
                    1: datetime.date(2001, 5, 2),
                    2: datetime.date(2001, 5, 7),
                },
            }
        ),
    ),
    (
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 33 110 31 31 'OPEN'  /
     'OP2' 66 110 31 31 'OPEN'  /
    /

    WELOPEN
     'OP2' 'OPEN' /
    /

    DATES
     2 MAY 2001 /
    /

    COMPDAT
     'OP1' 34 111 32 32 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' /
    /

    DATES
     3 MAY 2001 /
    /

    WELOPEN
     'OP1' 'OPEN' /
     'OP2' 'SHUT' /
    /
    """,
        pd.DataFrame(
            {
                "WELL": {
                    0: "OP1",
                    1: "OP2",
                    2: "OP1",
                    3: "OP1",
                    4: "OP1",
                    5: "OP1",
                    6: "OP2",
                },
                "I": {0: 33, 1: 66, 2: 33, 3: 34, 4: 33, 5: 34, 6: 66},
                "J": {0: 110, 1: 110, 2: 110, 3: 111, 4: 110, 5: 111, 6: 110},
                "K1": {0: 31, 1: 31, 2: 31, 3: 32, 4: 31, 5: 32, 6: 31},
                "K2": {0: 31, 1: 31, 2: 31, 3: 32, 4: 31, 5: 32, 6: 31},
                "OP/SH": {
                    0: "OPEN",
                    1: "OPEN",
                    2: "SHUT",
                    3: "SHUT",
                    4: "OPEN",
                    5: "OPEN",
                    6: "SHUT",
                },
                "DATE": {
                    0: datetime.date(2001, 5, 1),
                    1: datetime.date(2001, 5, 1),
                    2: datetime.date(2001, 5, 2),
                    3: datetime.date(2001, 5, 2),
                    4: datetime.date(2001, 5, 3),
                    5: datetime.date(2001, 5, 3),
                    6: datetime.date(2001, 5, 3),
                },
            }
        ),
    ),
    (
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 33 110 1 2 'OPEN'  /
    /

    WELOPEN
     'OP1' 'SHUT' 33 110 1 /
    /

    DATES
     2 MAY 2001 /
    /

    WELOPEN
     'OP1' 'SHUT' 33 110 2 /
    /

    DATES
     3 MAY 2001 /
    /

    WELOPEN
     'OP1' 'OPEN' /
    /
    """,
        pd.DataFrame(
            {
                "WELL": {0: "OP1", 1: "OP1", 2: "OP1", 3: "OP1", 4: "OP1"},
                "I": {0: 33, 1: 33, 2: 33, 3: 33, 4: 33},
                "J": {0: 110, 1: 110, 2: 110, 3: 110, 4: 110},
                "K1": {0: 2, 1: 1, 2: 2, 3: 1, 4: 2},
                "K2": {0: 2, 1: 1, 2: 2, 3: 1, 4: 2},
                "OP/SH": {0: "OPEN", 1: "SHUT", 2: "SHUT", 3: "OPEN", 4: "OPEN"},
                "DATE": {
                    0: datetime.date(2001, 5, 1),
                    1: datetime.date(2001, 5, 1),
                    2: datetime.date(2001, 5, 2),
                    3: datetime.date(2001, 5, 3),
                    4: datetime.date(2001, 5, 3),
                },
            }
        ),
    ),
    (
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 1 1 1 1 'OPEN'  /
    /

    WELOPEN
     'OP1' 'SHUT' /
    /
    """,
        pd.DataFrame(
            {
                "WELL": {0: "OP1"},
                "I": {0: 1},
                "J": {0: 1},
                "K1": {0: 1},
                "K2": {0: 1},
                "OP/SH": {0: "SHUT"},
                "DATE": {0: datetime.date(2001, 5, 1)},
            }
        ),
    ),
    (
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 1 1 1 1 'OPEN'  /
    /

    DATES
     2 MAY 2001 /
    /

    WELOPEN
     'OP1' 'SHUT' /
    /

    COMPDAT
     'OP1' 1 1 1 1 'OPEN'  /
    /
    """,
        pd.DataFrame(
            {
                "WELL": {0: "OP1", 1: "OP1"},
                "I": {0: 1, 1: 1},
                "J": {0: 1, 1: 1},
                "K1": {0: 1, 1: 1},
                "K2": {0: 1, 1: 1},
                "OP/SH": {0: "OPEN", 1: "OPEN"},
                "DATE": {0: datetime.date(2001, 5, 1), 1: datetime.date(2001, 5, 2)},
            }
        ),
    ),
    (
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 1 1 1 2 'OPEN'  /
    /

    WELOPEN
     'OP1' 'SHUT' 1 1 1 /
    /
    """,
        pd.DataFrame(
            {
                "WELL": {0: "OP1", 1: "OP1"},
                "I": {0: 1, 1: 1},
                "J": {0: 1, 1: 1},
                "K1": {0: 2, 1: 1},
                "K2": {0: 2, 1: 1},
                "OP/SH": {0: "OPEN", 1: "SHUT"},
                "DATE": {0: datetime.date(2001, 5, 1), 1: datetime.date(2001, 5, 1)},
            }
        ),
    ),
    (
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 1 1 1 1 'OPEN'  /
    /

    WELOPEN
     'OP1' 'SHUT' /
    /

    WELOPEN
     'OP1' 'OPEN' /
    /
    """,
        pd.DataFrame(
            {
                "WELL": {0: "OP1"},
                "I": {0: 1},
                "J": {0: 1},
                "K1": {0: 1},
                "K2": {0: 1},
                "OP/SH": {0: "OPEN"},
                "DATE": {0: datetime.date(2001, 5, 1)},
            }
        ),
    ),
    (
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 1 1 1 1 'OPEN'  /
    /

    WELOPEN
     'OP1' 'OPEN' /
     'OP1' 'SHUT' /
    /
    """,
        pd.DataFrame(
            {
                "WELL": {0: "OP1"},
                "I": {0: 1},
                "J": {0: 1},
                "K1": {0: 1},
                "K2": {0: 1},
                "OP/SH": {0: "SHUT"},
                "DATE": {0: datetime.date(2001, 5, 1)},
            }
        ),
    ),
    (
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 1 1 1 2 'SHUT'  /
    /

    WELOPEN
     'OP1' 'OPEN' /
     'OP1' 'SHUT' 1 1 1 /
    /
    """,
        pd.DataFrame(
            {
                "WELL": {0: "OP1", 1: "OP1"},
                "I": {0: 1, 1: 1},
                "J": {0: 1, 1: 1},
                "K1": {0: 2, 1: 1},
                "K2": {0: 2, 1: 1},
                "OP/SH": {0: "OPEN", 1: "SHUT"},
                "DATE": {0: datetime.date(2001, 5, 1), 1: datetime.date(2001, 5, 1)},
            }
        ),
    ),
    # Test 0 values for ijk-connections
    (
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 1 1 1 2 'OPEN'  /
    /

    WELOPEN
     'OP1' 'SHUT' 0 0 0 2* /
    /
    """,
        pd.DataFrame(
            {
                "WELL": {0: "OP1", 1: "OP1"},
                "I": {0: 1, 1: 1},
                "J": {0: 1, 1: 1},
                "K1": {0: 2, 1: 1},
                "K2": {0: 2, 1: 1},
                "OP/SH": {0: "SHUT", 1: "SHUT"},
                "DATE": {0: datetime.date(2001, 5, 1), 1: datetime.date(2001, 5, 1)},
            }
        ),
    ),
    # Test wildcard in wellname
    (
        """
    DATES
      1 JAN 2000 /
    /
    COMPDAT
     'B_1H' 1 1 1 1 'OPEN' /
     'B_2H' 2 2 2 2 'OPEN' /
     'WI1' 3 3 3 3 'OPEN' /
    /
    WELOPEN
     'B*H' 'SHUT' /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "B_1H", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 1, 1), "B_2H", 2, 2, 2, 2, "SHUT"],
                [datetime.date(2000, 1, 1), "WI1", 3, 3, 3, 3, "OPEN"],
            ],
        ),
    ),
    # ? notation in WELOPEN is not implemented and fails
    pytest.param(
        """
    DATES
      1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     '?' 'SHUT' /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
        marks=pytest.mark.xfail(
            raises=ValueError, match="? notation in WELOPEN not implemented"
        ),
    ),
    # Test wildcard in the beginning of a wellname
    # Must be written as \*, because wellnames starting with *
    # are WLIST elements by definition.
    (
        """
    DATES
      1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     '\\*P1' 'SHUT' /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
    ),
    # Test wildcard in wellname. A well that also matches the well template
    # but is defined later, is not SHUT
    (
        """
    DATES
      1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
     'OP2' 2 2 2 2 'OPEN' /
     'WI1' 3 3 3 3 'OPEN' /
    /
    WELOPEN
     'OP*' 'SHUT' /
    /
    DATES
      1 FEB 2000 /
    /
    COMPDAT
      'OP3' 4 4 4 4 'OPEN' /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 1, 1), "OP2", 2, 2, 2, 2, "SHUT"],
                [datetime.date(2000, 1, 1), "WI1", 3, 3, 3, 3, "OPEN"],
                [datetime.date(2000, 2, 1), "OP3", 4, 4, 4, 4, "OPEN"],
            ],
        ),
    ),
]


@pytest.mark.parametrize("test_input,expected", WELOPEN_CASES)
def test_welopen(test_input, expected):
    """Test with WELOPEN present"""
    deck = EclFiles.str2deck(test_input)
    compdf = compdat.deck2dfs(deck)["COMPDAT"]

    columns_to_check = ["WELL", "I", "J", "K1", "K2", "OP/SH", "DATE"]
    assert (
        compdf[columns_to_check]
        .sort_values(by=columns_to_check, axis=0)
        .reset_index()[columns_to_check]
        == expected[columns_to_check]
        .sort_values(by=columns_to_check, axis=0)
        .reset_index()[columns_to_check]
    ).all(axis=None)


@pytest.mark.parametrize(
    # It should only be necessary to test "NEW" actions in WLIST here, as the
    # transformation from ADD/DEL/MOV into NEW is tested in test_wlist
    "test_input, expected",
    [
        # Simplest case with one well in list
        (
            """
    DATES
      1 JAN 2000 /
    /
    COMPDAT
      'OP1' 1 1 1 1 'OPEN' /
    /
    WLIST
      '*OP' NEW OP1 /
    /
    WELOPEN
      '*OP' 'SHUT' /
    /
    """,
            pd.DataFrame(
                columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
                data=[
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                ],
            ),
        ),
        # WLIST for a different well
        pytest.param(
            """
    DATES
      1 JAN 2000 /
    /
    COMPDAT
      'OP1' 1 1 1 1 'OPEN' /
    /
    WLIST
      '*OP' NEW OP2 /
    /
    WELOPEN
      '*OP' 'SHUT' /
    /
    """,
            None,
            marks=pytest.mark.xfail(
                raises=ValueError, match="A WELOPEN keyword is not acting"
            ),
        ),
        # Two wells.
        (
            """
    DATES
      1 JAN 2000 /
    /
    COMPDAT
      'OP1' 1 1 1 1 'OPEN' /
      'OP2' 1 1 1 1 'OPEN' /
    /
    WLIST
      '*OP' NEW OP1 OP2/
    /
    WELOPEN
      -- Shut the wells immediately, overriding OPEN in COMPDAT
      '*OP' 'SHUT' /
    /
    """,
            pd.DataFrame(
                columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
                data=[
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                    [datetime.date(2000, 1, 1), "OP2", 1, 1, 1, 1, "SHUT"],
                ],
            ),
        ),
        # Four wells, two lists.
        (
            """
    DATES
      1 JAN 2000 /
    /
    COMPDAT
      'OP1' 1 1 1 1 'OPEN' /
      'OP2' 1 1 1 1 'OPEN' /
      'IN1' 2 1 1 1 'OPEN' /
      'IN2' 2 1 1 1 'OPEN' /
    /
    WELOPEN
      -- In ecl2df, the WELOPEN is allowed to be before WLIST
      '*OP' 'SHUT' /
    /
    WLIST
      '*OP' NEW OP1 OP2 /
      '*IN' NEW IN1 IN2 /
    /
    DATES
      2 JAN 2000 /
    /
    WELOPEN
      '*IN' 'SHUT' /
    /
    """,
            pd.DataFrame(
                columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
                data=[
                    [datetime.date(2000, 1, 1), "IN1", 2, 1, 1, 1, "OPEN"],
                    [datetime.date(2000, 1, 1), "IN2", 2, 1, 1, 1, "OPEN"],
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                    [datetime.date(2000, 1, 1), "OP2", 1, 1, 1, 1, "SHUT"],
                    [datetime.date(2000, 1, 2), "IN1", 2, 1, 1, 1, "SHUT"],
                    [datetime.date(2000, 1, 2), "IN2", 2, 1, 1, 1, "SHUT"],
                ],
            ),
        ),
        # WLIST defined too late
        pytest.param(
            """
    DATES
      1 JAN 2000 /
    /
    COMPDAT
      'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
      '*OP' 'SHUT' /
    /
    DATES
      2 JAN 2000/
    /
    WLIST
      '*OP' NEW OP2 /
    /
    """,
            None,
            id="futurewlist",
            marks=pytest.mark.xfail(
                raises=ValueError, match="Well list OP not defined at 2000-01-01"
            ),
        ),
        pytest.param(
            # WELOPEN on non-existing well list name
            """
    DATES
      1 JAN 2000 /
    /
    COMPDAT
      'OP1' 1 1 1 1 'OPEN' /
    /
    WLIST
      '*OP' NEW OP1 /
    /
    WELOPEN
      '*OPS' 'SHUT' /
    /
    """,
            None,
            marks=pytest.mark.xfail(
                raises=ValueError, match="Well list OPS not defined at 2000-01-01"
            ),
        ),
        # WLIST that has been redefined
        pytest.param(
            """
    DATES
      1 JAN 1999/
    /
    WLIST
      '*OP' NEW OP9 /
    /
    DATES
      1 JAN 2000 /
    /
    COMPDAT
      'OP1' 1 1 1 1 'OPEN' /
    /
    WLIST
      '*OP' NEW OP1 /
    /
    WELOPEN
      '*OP' 'SHUT' /
    /
    """,
            pd.DataFrame(
                columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
                data=[
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                ],
            ),
            id="redefined_wlist",
        ),
    ],
)
def test_welopen_wlist(test_input, expected):
    deck = EclFiles.str2deck(test_input)
    dfs = compdat.deck2dfs(deck)
    pd.testing.assert_frame_equal(dfs["COMPDAT"][expected.columns], expected)


@pytest.mark.parametrize(
    "test_input, expected",
    [
        # Simplest possible case
        (
            """
DATES
    1 JAN 2000 /
/
COMPDAT
    'OP1' 1 1 1 1 'OPEN' /
/
COMPLUMP
    'OP1' 1 1 1 1 1 /
/
WELOPEN
    'OP1' 'SHUT' 3* 1 1 /
/
    """,
            pd.DataFrame(
                columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
                data=[
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                ],
            ),
        ),
        # Range of Ks in COMPDAT/COMPLUMP and multiple dates
        (
            """
DATES
    1 JAN 2000 /
/
COMPDAT
    'OP1' 1 1 1 3 'OPEN' /
/
COMPLUMP
    'OP1' 1 1 1 2 1 /
/
DATES
    1 FEB 2000 /
/
WELOPEN
    'OP1' 'SHUT' 3* 1 1 /
/
    """,
            pd.DataFrame(
                columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
                data=[
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "OPEN"],
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 2, 2, "OPEN"],
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 3, 3, "OPEN"],
                    [datetime.date(2000, 2, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                    [datetime.date(2000, 2, 1), "OP1", 1, 1, 2, 2, "SHUT"],
                ],
            ),
        ),
        # Range of COMPLUMPs in WELOPEN
        (
            """
DATES
    1 JAN 2000 /
/
COMPDAT
    'OP1' 1 1 1 5 'OPEN' /
/
COMPLUMP
    'OP1' 1 1 1 2 1 /
    'OP1' 1 1 3 4 2 /
    'OP1' 1 1 5 5 3 /
/
WELOPEN
    'OP1' 'SHUT' 3* 1 2 /
/
    """,
            pd.DataFrame(
                columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
                data=[
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 5, 5, "OPEN"],
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 2, 2, "SHUT"],
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 3, 3, "SHUT"],
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 4, 4, "SHUT"],
                ],
            ),
        ),
        # Test default handling in COMPLUMP. Default value 0 means all values
        # of this coordinate
        # This fails for now, but dataframe is indicating wanted behavior
        pytest.param(
            """
DATES
    1 JAN 2000 /
/
COMPDAT
    'OP1' 1 1 1 2 'OPEN' /
    'OP1' 2 1 1 1 'OPEN' /
/
COMPLUMP
    'OP1' 1 0 0 0 1 /
/
WELOPEN
    'OP1' 'SHUT' 3* 1 1 /
/
    """,
            pd.DataFrame(
                columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
                data=[
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 2, 2, "SHUT"],
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "OPEN"],
                ],
            ),
            id="complump_defaults",
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            # Fails when K2<K1 in COMPLUMP
            """
COMPDAT
    'OP1' 1 1 1 2 'OPEN' /
/
COMPLUMP
    'OP1' 1 1 2 1 1 /
/
WELOPEN
    'OP1' 'SHUT' 3* 1 1 /
/
""",
            None,
            id="complump_K2lessthanK1",
            marks=pytest.mark.xfail(
                raises=ValueError, match="K2 must be equal to or greater than K1"
            ),
        ),
        pytest.param(
            # Fails when only one completion number is defined in WELOPEN
            """
COMPDAT
    'OP1' 1 1 1 1 'OPEN' /
/
COMPLUMP
    'OP1' 1 1 1 1 1 /
/
WELOPEN
    'OP1' 'SHUT' 3* 1 /
/
""",
            None,
            id="complump_missingcompletion_number",
            marks=pytest.mark.xfail(
                raises=ValueError,
                match=(
                    "Both or none of the completions numbers "
                    "in WELOPEN must be defined."
                ),
            ),
        ),
        pytest.param(
            # Fails when C2<C1 in WELOPEN
            """
COMPDAT
    'OP1' 1 1 1 2 'OPEN' /
/
COMPLUMP
    'OP1' 1 1 1 1 1 /
    'OP1' 1 1 2 2 2 /
/
WELOPEN
    'OP1' 'SHUT' 3* 2 1 /
/
""",
            None,
            marks=pytest.mark.xfail(
                raises=ValueError, match="C2 must be equal or greater than C1"
            ),
        ),
        pytest.param(
            # Fails when C2<C1 in WELOPEN
            """
COMPDAT
    'OP1' 1 1 1 1 'OPEN' /
/
COMPLUMP
    'OP1' -1 -1 -1 -1 1 /
/
WELOPEN
    'OP1' 'SHUT' 3* 1 1 /
/
""",
            None,
            id="complump_negativevalues",
            marks=pytest.mark.xfail(
                raises=ValueError,
                match="Negative values for COMPLUMP coordinates are not allowed",
            ),
        ),
    ],
)
def test_welopen_complump(test_input, expected):
    deck = EclFiles.str2deck(test_input)
    dfs = compdat.deck2dfs(deck)
    pd.testing.assert_frame_equal(dfs["COMPDAT"][expected.columns], expected)
