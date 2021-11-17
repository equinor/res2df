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

WELOPEN_CASES = [
    # WELOPEN SHUT closes both well and connections
    pytest.param(
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
        id="welopen-shut",
    ),
    # WELOPEN SHUT with explicit defaults, still closes both well and connections
    pytest.param(
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
        id="welopen-shut-explicit-defaults",
    ),
    # Test the zero handling in WELOPEN (zero value means apply to all)
    pytest.param(
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
        id="zero-values",
    ),
    # Test the defaults handling in WELOPEN (default values are negative)
    pytest.param(
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
        id="negative-values",
    ),
    # When item 3-7 are defaulted, the action applies to the well and not the
    # connections. Thus they should be kept open.
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'STOP' /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "OPEN"],
            ],
        ),
        id="welopen-stop-on-well",
    ),
    # Both 1*, 0 and -1 are default values and give the same result:
    # When all coordinates are defaulted, the connections are left OPEN
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
     'OP2' 1 1 1 1 'OPEN' /
     'OP3' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'STOP' 1* 1* 1* /
     'OP2' 'STOP' 0  0  0  /
     'OP3' 'STOP' -1 -1 -1 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "OPEN"],
                [datetime.date(2000, 1, 1), "OP2", 1, 1, 1, 1, "OPEN"],
                [datetime.date(2000, 1, 1), "OP3", 1, 1, 1, 1, "OPEN"],
            ],
        ),
        id="welopen-stop-on-well-explicit-defaults",
    ),
    # In this test, the well connection is first SHUT, but then
    # actually opened by applying STOP on the well. The well is still
    # closed but the connection is open. Note that applying STOP to
    # the connection instead of the well ('OP1' 'STOP' 1 1 1 /) would
    # leave the connection still shut. This behavior has been tested
    # in the simulator.
    pytest.param(
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
    DATES
     1 FEB 2000 /
    /
    WELOPEN
     'OP1' 'STOP' /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 2, 1), "OP1", 1, 1, 1, 1, "OPEN"],
            ],
        ),
        id="welopen-shut-then-stop-on-well",
    ),
    # Closes a connection with specified I, J, K
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' 1 1 1 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
        id="welopen-shut-on-connection",
    ),
    # Test when one coordinate is defaulted. Shuts all connections in the
    # well with J==1 and K==1
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
     'OP1' 2 1 1 1 'OPEN' /
     'OP1' 1 1 2 2 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' 0 1 1 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 2, 2, "OPEN"],
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 1, 1), "OP1", 2, 1, 1, 1, "SHUT"],
            ],
        ),
        id="welopen-with-defaulted-I-coordinate",
    ),
    # Test that all combinations of two defaulted coordinates are working
    # And that defaulting with *, 0 and -1 is treated the same
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 2 'OPEN' /
     'OP2' 1 1 1 1 'OPEN' /
     'OP2' 2 2 2 2 'OPEN' /
     'OP3' 1 1 1 1 'OPEN' /
     'OP3' 2 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' 2*    1 /
     'OP2' 'SHUT' 0  1  0 /
     'OP3' 'SHUT' 1 -1 -1 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP2", 2, 2, 2, 2, "OPEN"],
                [datetime.date(2000, 1, 1), "OP3", 2, 1, 1, 1, "OPEN"],
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 2, 2, "OPEN"],
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 1, 1), "OP2", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 1, 1), "OP3", 1, 1, 1, 1, "SHUT"],
            ],
        ),
        id="welopen-combinations-of-defaulted-coordinates",
    ),
    # Both wilcard well name and K coordinate defaulted
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1'  1 1 1 1 'OPEN' /
     'OP2'  1 1 2 2 'OPEN' /
     'PROD' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP*'  'SHUT' 1 1 0 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "PROD", 1, 1, 1, 1, "OPEN"],
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 1, 1), "OP2", 1, 1, 2, 2, "SHUT"],
            ],
        ),
        id="both-wildcard-wellname-and-defaulted-coordinates",
    ),
    # Compdat changing with time. The WELOPEN statement is only acting on
    # connections that have been defined at that date. In this test, the
    # connections with I==1 and I==2 will be SHUT, but not I==3
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1'  1 1 1 1 'OPEN' /
    /
    DATES
     1 FEB 2000 /
    /
    COMPDAT
     'OP1'  2 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1'  'SHUT' 0 1 1 /
    /
    DATES
     1 MAR 2000 /
    /
    COMPDAT
     'OP1'  3 1 1 1 'OPEN' /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "OPEN"],
                [datetime.date(2000, 2, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 2, 1), "OP1", 2, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 3, 1), "OP1", 3, 1, 1, 1, "OPEN"],
            ],
        ),
        id="welopen-defaults-compdat-changing-with-time",
    ),
    # Welopen defaults with START instead of DATES in the first timestep
    pytest.param(
        """
    START
     1 JAN 2000 /
    /
    COMPDAT
     'OP1'  1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1'  'SHUT' 0 1 1 /
    /

    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
        id="welopen-defaults-start",
    ),
    # No dates at all
    pytest.param(
        """
    COMPDAT
     'OP1'  1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1'  'SHUT' 0 1 1 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [None, "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
        id="welopen-defaults-no-dates",
    ),
    # No start date, then a date later
    pytest.param(
        """
    COMPDAT
     'OP1'  1 1 1 1 'OPEN' /
    /
    DATES
     1 JAN 2000 /
    /
    WELOPEN
     'OP1'  'SHUT' 0 1 1 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [None, "OP1", 1, 1, 1, 1, "OPEN"],
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
        id="welopen-defaults-no-start-date",
    ),
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1'  1 1 1 2 'OPEN' /
    /
    WELOPEN
     'OP1'  'SHUT' 0 0 3 /
    /
    """,
        None,
        id="no-connections-matching-welopen-defaults",
        marks=pytest.mark.xfail(
            raises=ValueError,
            match="No connections are matching WELOPEN keyword",
        ),
    ),
    # Defaulted COMPLUMPs in WELOPEN not supported
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1'  1 1 1 2 'OPEN' /
    /
    COMPLUMP
     'OP1' 1 1 1 1 1 /
     'OP1' 1 1 1 1 2 /
    /

    WELOPEN
     'OP1'  'SHUT' 3* 1 0 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 2, 2, "SHUT"],
            ],
        ),
        id="defaulted-complump-in-welopen-not-supported",
        marks=pytest.mark.xfail(
            raises=ValueError,
            match="Zeros for C1/C2 is not implemented",
        ),
    ),
    # STOP on connection is the same as SHUT
    # (note that STOP on well gives OPEN connections)
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'STOP' 1 1 1 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
            ],
        ),
        id="welopen-stop-on-connection-is-shut",
    ),
    # POPN is the same as OPEN
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'POPN' 1 1 1 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "OPEN"],
            ],
        ),
        id="welopen-popn-on-connection-is-open",
    ),
    # WELOPEN refers to a lumped connection, but COMPLUMP is missing
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' 1 1 1 1 1 /
    /
    """,
        None,
        id="complump_missing",
        marks=pytest.mark.xfail(raises=ValueError),
    ),
    # Well is missing
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP2' 'SHUT' 1 1 1 /
    /
    """,
        None,
        id="operating-on-unknown-well",
        marks=pytest.mark.xfail(raises=ValueError),
    ),
    # Test J slicing
    pytest.param(
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
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 3, 3, "OPEN"],
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 2, 2, "SHUT"],
            ],
        ),
        id="j-slicing",
    ),
    # Test multiple connections to the same cell
    pytest.param(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
     'OP2' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' 0 0 0 /
     'OP2' 'OPEN' 0 0 0 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 1, 1), "OP2", 1, 1, 1, 1, "OPEN"],
            ],
        ),
        id="multiple-connnections-same-cell",
    ),
    # Test multiple time steps
    pytest.param(
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 33 110 31 31 'OPEN'  /
    /

    WELOPEN
     'OP1' 'SHUT' 0 0 0 /
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
        id="multiple-time-steps",
    ),
    pytest.param(
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 33 110 31 31 'OPEN'  /
    /

    WELOPEN
     'OP1' 'OPEN' 0 0 0/
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
        id="more-time-steps",
    ),
    pytest.param(
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 33 110 31 31 'OPEN'  /
     'OP2' 66 110 31 31 'OPEN'  /
    /

    WELOPEN
     'OP2' 'OPEN' 0 0 0/
    /

    DATES
     2 MAY 2001 /
    /

    COMPDAT
     'OP1' 34 111 32 32 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' 0 0 0 /
    /

    DATES
     3 MAY 2001 /
    /

    WELOPEN
     'OP1' 'OPEN' 0 0 0 /
     'OP2' 'SHUT' 0 0 0 /
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
        id="date-stepping",
    ),
    pytest.param(
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
     'OP1' 'OPEN' 0 0 0 /
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
        id="more-date-stepping",
    ),
    pytest.param(
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
        id="test-xx1",
    ),
    pytest.param(
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 1 1 1 1 'OPEN'  /
    /

    WELOPEN
     'OP1' 'OPEN' 0 0 0 /
     'OP1' 'SHUT' 0 0 0 /
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
        id="self-overwriting-records",
    ),
    pytest.param(
        """
    DATES
     1 MAY 2001 /
    /

    COMPDAT
     'OP1' 1 1 1 2 'SHUT'  /
    /

    WELOPEN
     'OP1' 'OPEN' 0 0 0 /
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
        id="open-and-shut-slice-multiple-welopen",
    ),
    # Referencing multiple wells with wildcards
    # Wildcard structures are tested in test_common and need
    # not be tested here.
    pytest.param(
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
     'B*H' 'SHUT' 0 0 0 /
    /
    """,
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
            data=[
                [datetime.date(2000, 1, 1), "WI1", 3, 3, 3, 3, "OPEN"],
                [datetime.date(2000, 1, 1), "B_1H", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 1, 1), "B_2H", 2, 2, 2, 2, "SHUT"],
            ],
        ),
        id="multiple-wells-via-wildcard",
    ),
    # Test wildcard in wellname. A well that also matches the well template
    # but is defined later, is not SHUT
    pytest.param(
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
     'OP*' 'SHUT' 0 0 0 /
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
                [datetime.date(2000, 1, 1), "WI1", 3, 3, 3, 3, "OPEN"],
                [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                [datetime.date(2000, 1, 1), "OP2", 2, 2, 2, 2, "SHUT"],
                [datetime.date(2000, 2, 1), "OP3", 4, 4, 4, 4, "OPEN"],
            ],
        ),
        id="wildcards-do-not-apply-to-future-wells",
    ),
]


@pytest.mark.parametrize("test_input, expected", WELOPEN_CASES)
def test_welopen(test_input, expected):
    """Test with WELOPEN present"""
    deck = EclFiles.str2deck(test_input)
    compdf = compdat.deck2dfs(deck)["COMPDAT"]
    columns_to_check = ["WELL", "I", "J", "K1", "K2", "OP/SH", "DATE"]

    pd.testing.assert_frame_equal(compdf[columns_to_check], expected[columns_to_check])


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
      '*OP' 'SHUT' 0 0 0 /
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
      '*OP' 'SHUT' 0 0 0 /
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
      '*OP' 'SHUT' 0 0 0 /
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
      '*OP' 'SHUT' 0 0 0 /
    /
    WLIST
      '*OP' NEW OP1 OP2 /
      '*IN' NEW IN1 IN2 /
    /
    DATES
      2 JAN 2000 /
    /
    WELOPEN
      '*IN' 'SHUT' 0 0 0 /
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
      '*OP' 'SHUT' 0 0 0 /
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
      '*OPS' 'SHUT' 0 0 0 /
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
      '*OP' 'SHUT' 0 0 0 /
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


def test_welopen_df():
    """Test that we can obtain WELOPEN information when it applies on well state,
    not on connections."""
    deck = EclFiles.str2deck(
        """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
    /
    WELOPEN
     'OP1' 'SHUT' / -- This is ignored for connections
    /
    """
    )
    print(compdat.deck2dfs(deck)["WELOPEN"])
    pd.testing.assert_frame_equal(
        compdat.deck2dfs(deck)["WELOPEN"],
        pd.DataFrame(
            columns=[
                "DATE",
                "WELL",
                "I",
                "J",
                "K",
                "C1",
                "C2",
                "STATUS",
                "KEYWORD_IDX",
            ],
            data=[
                [
                    datetime.date(2000, 1, 1),
                    "OP1",
                    None,
                    None,
                    None,
                    None,
                    None,
                    "SHUT",
                    2,
                ],
            ],
        ),
        check_like=True,
    )


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
            marks=pytest.mark.xfail(
                raises=ValueError,
                match="Defaulted COMPLUMP coordinates are not supported in ecl2df",
            ),
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
            id="complump_K2<K1",
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
            id="welopen_C2<C1",
            marks=pytest.mark.xfail(
                raises=ValueError, match="C2 must be equal or greater than C1"
            ),
        ),
        pytest.param(
            # Fails for negative numbers in COMPLUMP row
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
        pytest.param(
            # Fails for negative completion numbers in welopen
            """
COMPDAT
    'OP1' 1 1 1 1 'OPEN' /
/
COMPLUMP
    'OP1' 1 1 1 1 /
/
WELOPEN
    'OP1' 'SHUT' 3* -1 -1 /
/
""",
            None,
            id="welopen_negative_completionvalues",
            marks=pytest.mark.xfail(
                raises=ValueError,
                match="Negative values for C1/C2 is no allowed",
            ),
        ),
        pytest.param(
            # Fails for default completionvalues (zero) in WELOPEN
            """
COMPDAT
    'OP1' 1 1 1 1 'OPEN' /
/
COMPLUMP
    'OP1' 1 1 1 1 /
/
WELOPEN
    'OP1' 'SHUT' 3* 0 0 /
/
""",
            None,
            id="welopen_default_complumpvalues",
            marks=pytest.mark.xfail(
                raises=ValueError,
                match="Defaults (zero) for C1/C2 is not implemented",
            ),
        ),
        pytest.param(
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
     'OP1' 'SHUT' 1 1 1 1 1 /
    /
    """,
            pd.DataFrame(
                columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
                data=[
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                ],
            ),
            id="indices_and_complump_combined",
        ),
        pytest.param(
            """
    DATES
     1 JAN 2000 /
    /
    COMPDAT
     'OP1' 1 1 1 1 'OPEN' /
     'OP1' 1 1 2 2 'OPEN' /
    /
    COMPLUMP
     -- Assign completion number 1 and 2 to the two connections
     'OP1' 1 1 1 1 1 /
     'OP1' 1 1 2 2 2 /
    /
    WELOPEN
     -- This is ok, gives shut well:
     'OP1' 'SHUT' 1 1 1 1 1 /  -- must match both i,j,k and complump
     -- The following is ignored, because completion 2 is not at 1,1,1
     'OP1' 'SHUT' 1 1 1 2 2 /
    /
    """,
            pd.DataFrame(
                columns=["DATE", "WELL", "I", "J", "K1", "K2", "OP/SH"],
                data=[
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 2, 2, "OPEN"],
                    [datetime.date(2000, 1, 1), "OP1", 1, 1, 1, 1, "SHUT"],
                ],
            ),
            id="indices_and_complump_combined_2",
        ),
    ],
)
def test_welopen_complump(test_input, expected):
    """Test the welopen_complump functionality through Eclipse decks"""
    deck = EclFiles.str2deck(test_input)
    dfs = compdat.deck2dfs(deck)
    pd.testing.assert_frame_equal(dfs["COMPDAT"][expected.columns], expected)


@pytest.mark.parametrize(
    "welopen, complump, expected",
    [
        pytest.param([], [], [], id="empty_input_empty_output"),
        pytest.param(
            [{"FOO": "BAR"}],
            [],
            [{"FOO": "BAR"}],
            id="empty_complump_pass_through_welopen",
        ),
        pytest.param(
            [{"WELL": "OP1", "C1": None, "C2": None}],
            [],
            [{"WELL": "OP1", "C1": None, "C2": None}],
            id="pass_through_None_complumps",
        ),
        pytest.param(
            [{"WELL": "OP1", "DATE": datetime.date(2000, 1, 1), "C1": 1, "C2": 1}],
            [
                {
                    "WELL": "OP1",
                    "DATE": datetime.date(2000, 1, 1),
                    "STATUS": "OPEN",
                    "I": 2,
                    "J": 2,
                    "K1": 2,
                    "K2": 2,
                    "N": 1,
                }
            ],
            [
                {
                    "WELL": "OP1",
                    "DATE": datetime.date(2000, 1, 1),
                    "C1": None,
                    "C2": None,
                    "I": 2,
                    "J": 2,
                    "K": 2,
                }
            ],
            id="basic",
        ),
        pytest.param(
            [{"WELL": "OP1", "DATE": datetime.date(2000, 1, 1), "C1": 1, "C2": 1}],
            [
                {
                    "WELL": "OP1",
                    "DATE": datetime.date(2000, 1, 1),
                    "STATUS": "OPEN",
                    "I": 2,
                    "J": 2,
                    "K1": 2,
                    "K2": 3,
                    "N": 1,
                }
            ],
            [],
            id="k2_not_equal_kq_in_complump",
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ],
)
def test_welopen_complump_direct(welopen, complump, expected):
    """Test the welopen_complump directly.

    For situations not that easy to reach via string input."""
    pd.testing.assert_frame_equal(
        compdat.expand_complump_in_welopen_df(
            pd.DataFrame(welopen), pd.DataFrame(complump)
        ),
        pd.DataFrame(expected),
        check_dtype=False,
    )


@pytest.mark.parametrize(
    "compdat_rows, welopen_rows, wlist_rows, complump_rows, expected_rows",
    [
        pytest.param([], [], [], [], [], id="emptyinput"),
        pytest.param(
            [{"WELL": "OP1"}],
            [],
            [{"ACTION": "ADD"}],
            [],
            [],
            id="non-expanded_wlist",
            # "The WLIST dataframe must be expanded through expand_wlist()"
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            [{"WELL": "OP1", "I": 1, "J": 1, "K1": 1, "K2": 1}],
            [{"WELL": "OP1", "STATUS": "SHUT", "I": 0, "J": 0, "K": 0}],
            [],
            [],
            [],
            id="no_keyword_idx",
            # Column KEYWORD_IDX must be present in compdat rows
            marks=pytest.mark.xfail(raises=KeyError),
        ),
        pytest.param(
            [
                {
                    "WELL": "OP1",
                    "I": 1,
                    "J": 1,
                    "K1": 1,
                    "K2": 1,
                    "KEYWORD_IDX": 1,
                    "DATE": None,
                }
            ],
            [
                {
                    "WELL": "OP1",
                    "STATUS": "SHUT",
                    "I": 0,
                    "J": 0,
                    "K": 0,
                    "KEYWORD_IDX": 2,
                    "DATE": None,
                }
            ],
            [],
            [],
            [
                {
                    "WELL": "OP1",
                    "I": 1,
                    "J": 1,
                    "K1": 1,
                    "K2": 1,
                    "KEYWORD_IDX": 2,
                    "DATE": None,
                    "OP/SH": "SHUT",
                }
            ],
            id="working_example",
        ),
        pytest.param(
            [
                {
                    "WELL": "OP1",
                    "I": 1,
                    "J": 1,
                    "K1": 1,
                    "K2": 1,
                    "KEYWORD_IDX": 1,
                    "DATE": None,
                }
            ],
            [
                {
                    "WELL": "OP1",
                    "STATUS": "SHUT",
                    "I": 1,  # Either all zero or none nonzero
                    "J": 0,
                    "K": 0,
                    "KEYWORD_IDX": 2,
                    "DATE": None,
                }
            ],
            [],
            [],
            [],
            id="invalid welopen",
            # " A WELOPEN keyword contains data that could not be parsed"
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ],
)
def test_applywelopen(
    compdat_rows, welopen_rows, wlist_rows, complump_rows, expected_rows
):
    print(
        compdat.applywelopen(
            pd.DataFrame(compdat_rows),
            pd.DataFrame(welopen_rows),
            pd.DataFrame(wlist_rows),
            pd.DataFrame(complump_rows),
        ).to_dict(orient="records")
    )
    pd.testing.assert_frame_equal(
        compdat.applywelopen(
            pd.DataFrame(compdat_rows),
            pd.DataFrame(welopen_rows),
            pd.DataFrame(wlist_rows),
            pd.DataFrame(complump_rows),
        ),
        pd.DataFrame(expected_rows),
    )
