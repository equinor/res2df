import copy

import pandas as pd
import pytest

from res2df import ResdataFiles, vfp

try:
    import opm  # noqa
except ImportError:
    pytest.skip(
        "OPM is not installed",
        allow_module_level=True,
    )

VFPPROD_ARRAY_NAMES = [
    "THP_INDICES",
    "WFR_INDICES",
    "GFR_INDICES",
    "THP_VALUES",
    "FLOW_VALUES",
    "THP_VALUES",
    "WFR_VALUES",
    "GFR_VALUES",
    "BHP_TABLE",
]

VFPINJ_ARRAY_NAMES = [
    "THP_INDICES",
    "THP_VALUES",
    "FLOW_VALUES",
    "THP_VALUES",
    "BHP_TABLE",
]


VFPPROD_CASES = [
    # Test cases for VFPPROD
    pytest.param(
        """
VFPPROD

-- Table  Datum Depth  Rate Type  WFR Type  GFR Type  THP Type  ALQ Type  """
        + """UNITS   TAB Type
-- -----  -----------  ---------  --------  --------  --------  --------  """
        + """------  --------
       1       3000.0        GAS       WGR       GOR       THP        ''  """
        + """METRIC       BHP /

-- GAS units - sm3/day ( 3 values )
     50000     500000      5e+06  /

-- THP units - barsa ( 2 values )
        40        100  /

-- WGR units - sm3/sm3 ( 2 values )
         0      1e-05  /

-- GOR units - sm3/sm3 ( 2 values )
       500       4000  /

-- '' units -  ( 1 values )
         0  /

 1  1  1  1    160.11     130.21     180.31
/
 1  1  2  1    140.12     110.22     160.32
/
 1  2  1  1    165.13     135.23     185.33
/
 1  2  2  1    145.14     115.24     165.34
/
 2  1  1  1    240.15     210.25     260.35
/
 2  1  2  1    220.16     190.26     240.36
/
 2  2  1  1    245.17     215.27     265.37
/
 2  2  2  1    225.18     195.28     245.38
/
    """,
        pd.DataFrame(
            columns=[
                "RATE",
                "PRESSURE",
                "WFR",
                "GFR",
                "ALQ",
                "TAB",
                "VFP_TYPE",
                "TABLE_NUMBER",
                "DATUM",
                "RATE_TYPE",
                "WFR_TYPE",
                "GFR_TYPE",
                "ALQ_TYPE",
                "PRESSURE_TYPE",
                "TAB_TYPE",
                "UNIT_TYPE",
            ],
            data=[
                [
                    50000.0,
                    40.0,
                    0.0,
                    500.0,
                    0.0,
                    160.11,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    500000.0,
                    40.0,
                    0.0,
                    500.0,
                    0.0,
                    130.21,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    5000000.0,
                    40.0,
                    0.0,
                    500.0,
                    0.0,
                    180.31,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    50000.0,
                    40.0,
                    0.0,
                    4000.0,
                    0.0,
                    140.12,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    500000.0,
                    40.0,
                    0.0,
                    4000.0,
                    0.0,
                    110.22,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    5000000.0,
                    40.0,
                    0.0,
                    4000.0,
                    0.0,
                    160.32,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    50000.0,
                    40.0,
                    1e-05,
                    500.0,
                    0.0,
                    165.13,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    500000.0,
                    40.0,
                    1e-05,
                    500.0,
                    0.0,
                    135.23,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    5000000.0,
                    40.0,
                    1e-05,
                    500.0,
                    0.0,
                    185.33,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    50000.0,
                    40.0,
                    1e-05,
                    4000.0,
                    0.0,
                    145.14,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    500000.0,
                    40.0,
                    1e-05,
                    4000.0,
                    0.0,
                    115.24,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    5000000.0,
                    40.0,
                    1e-05,
                    4000.0,
                    0.0,
                    165.34,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    50000.0,
                    100.0,
                    0.0,
                    500.0,
                    0.0,
                    240.15,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    500000.0,
                    100.0,
                    0.0,
                    500.0,
                    0.0,
                    210.25,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    5000000.0,
                    100.0,
                    0.0,
                    500.0,
                    0.0,
                    260.35,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    50000.0,
                    100.0,
                    0.0,
                    4000.0,
                    0.0,
                    220.16,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    500000.0,
                    100.0,
                    0.0,
                    4000.0,
                    0.0,
                    190.26,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    5000000.0,
                    100.0,
                    0.0,
                    4000.0,
                    0.0,
                    240.36,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    50000.0,
                    100.0,
                    1e-05,
                    500.0,
                    0.0,
                    245.17,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    500000.0,
                    100.0,
                    1e-05,
                    500.0,
                    0.0,
                    215.27,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    5000000.0,
                    100.0,
                    1e-05,
                    500.0,
                    0.0,
                    265.37,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    50000.0,
                    100.0,
                    1e-05,
                    4000.0,
                    0.0,
                    225.18,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    500000.0,
                    100.0,
                    1e-05,
                    4000.0,
                    0.0,
                    195.28,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    5000000.0,
                    100.0,
                    1e-05,
                    4000.0,
                    0.0,
                    245.38,
                    "VFPPROD",
                    1,
                    3000.0,
                    "GAS",
                    "WGR",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
            ],
        ),
    ),
    pytest.param(
        """
VFPPROD

-- Table  Datum Depth
-- -----  -----------
       2       3000.0 /

-- GAS units - sm3/day ( 1 values )
     50000 /

-- THP units - barsa ( 1 values )
        40 /

-- WGR units - sm3/sm3 ( 1 values )
         0 /

-- GOR units - sm3/sm3 ( 1 values )
       500 /

-- "''" units -  ( 1 values )
         0 /

 1  1  1  1    160.11
/
    """,
        pd.DataFrame(
            columns=[
                "RATE",
                "PRESSURE",
                "WFR",
                "GFR",
                "ALQ",
                "TAB",
                "VFP_TYPE",
                "TABLE_NUMBER",
                "DATUM",
                "RATE_TYPE",
                "WFR_TYPE",
                "GFR_TYPE",
                "ALQ_TYPE",
                "PRESSURE_TYPE",
                "TAB_TYPE",
                "UNIT_TYPE",
            ],
            data=[
                [
                    50000.0,
                    40.0,
                    0.0,
                    500.0,
                    0.0,
                    160.11,
                    "VFPPROD",
                    2,
                    3000.0,
                    "GAS",
                    "WCT",
                    "GOR",
                    "''",
                    "THP",
                    "BHP",
                    "DEFAULT",
                ]
            ],
        ),
    ),
]

VFPINJ_CASES = [
    # Test cases for VFPINJ
    pytest.param(
        """
VFPINJ

-- Table  Datum Depth  Rate Type  THP Type  UNITS     TAB Type
-- -----  -----------  ---------  --------  --------  --------
       3       3200.0        GAS       THP    METRIC       BHP /

-- GAS units - sm3/day ( 3 values )
     50000     500000      5e+06  /

-- THP units - barsa ( 2 values )
       100        200  /

 1    180.11     170.21     150.31
/
 2    270.12     260.22     240.32
/
    """,
        pd.DataFrame(
            columns=[
                "RATE",
                "PRESSURE",
                "TAB",
                "VFP_TYPE",
                "TABLE_NUMBER",
                "DATUM",
                "RATE_TYPE",
                "PRESSURE_TYPE",
                "TAB_TYPE",
                "UNIT_TYPE",
            ],
            data=[
                [
                    50000.0,
                    100.0,
                    180.11,
                    "VFPINJ",
                    3,
                    3200.0,
                    "GAS",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    500000.0,
                    100.0,
                    170.21,
                    "VFPINJ",
                    3,
                    3200.0,
                    "GAS",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    5000000.0,
                    100.0,
                    150.31,
                    "VFPINJ",
                    3,
                    3200.0,
                    "GAS",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    50000.0,
                    200.0,
                    270.12,
                    "VFPINJ",
                    3,
                    3200.0,
                    "GAS",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    500000.0,
                    200.0,
                    260.22,
                    "VFPINJ",
                    3,
                    3200.0,
                    "GAS",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
                [
                    5000000.0,
                    200.0,
                    240.32,
                    "VFPINJ",
                    3,
                    3200.0,
                    "GAS",
                    "THP",
                    "BHP",
                    "METRIC",
                ],
            ],
        ),
    ),
    pytest.param(
        """
VFPINJ

-- Table  Datum Depth
-- -----  -----------
       4       3200.0 /

-- GAS units - sm3/day ( 1 values )
     50000 /

-- THP units - barsa ( 1 values )
       100 /

 1    180.11
/
    """,
        pd.DataFrame(
            columns=[
                "RATE",
                "PRESSURE",
                "TAB",
                "VFP_TYPE",
                "TABLE_NUMBER",
                "DATUM",
                "RATE_TYPE",
                "PRESSURE_TYPE",
                "TAB_TYPE",
                "UNIT_TYPE",
            ],
            data=[
                [
                    50000.0,
                    100.0,
                    180.11,
                    "VFPINJ",
                    4,
                    3200.0,
                    "GAS",
                    "THP",
                    "BHP",
                    "DEFAULT",
                ],
            ],
        ),
    ),
]

MULTIPLE_VFP_CASES = [
    pytest.param(
        """
VFPPROD

-- Table  Datum Depth  Rate Type  WFR Type  GFR Type  THP Type  ALQ Type  """
        + """UNITS   TAB Type
-- -----  -----------  ---------  --------  --------  --------  --------  """
        + """------  --------
       1       3000.0        GAS       WGR       GOR       THP        ''  """
        + """METRIC       BHP /

-- GAS units - sm3/day ( 1 values )
     50000 /

-- THP units - barsa ( 1 values )
        40 /

-- WGR units - sm3/sm3 ( 1 values )
         0 /

-- GOR units - sm3/sm3 ( 1 values )
       500 /

-- "''" units -  ( 1 values )
         0 /

 1  1  1  1    100.0
/

VFPPROD

-- Table  Datum Depth  Rate Type  WFR Type  GFR Type  THP Type  ALQ Type  """
        + """UNITS   TAB Type
-- -----  -----------  ---------  --------  --------  --------  --------  """
        + """------  --------
       2       4000.0        GAS       WGR       GOR       THP        ''  """
        + """METRIC       BHP /

-- GAS units - sm3/day ( 1 values )
     10000 /

-- THP units - barsa ( 1 values )
        10 /

-- WGR units - sm3/sm3 ( 1 values )
         0 /

-- GOR units - sm3/sm3 ( 1 values )
       50 /

-- "''" units -  ( 1 values )
         0 /

 1  1  1  1    200.0
/

VFPINJ

-- Table  Datum Depth  Rate Type  THP Type  UNITS     TAB Type
-- -----  -----------  ---------  --------  --------  --------
       3       3200.0        GAS       THP    METRIC       BHP /

-- GAS units - sm3/day ( 1 values )
     50000 /

-- THP units - barsa ( 1 values )
       100.0 /

 1    200.0
/

VFPINJ

-- Table  Datum Depth  Rate Type  THP Type  UNITS     TAB Type
-- -----  -----------  ---------  --------  --------  --------
       4       3200.0        GAS       THP    METRIC       BHP /

-- GAS units - sm3/day ( 1 values )
     50000 /

-- THP units - barsa ( 1 values )
       100.0 /

 1    200.0
/
    """,
        [
            pd.DataFrame(
                columns=[
                    "RATE",
                    "PRESSURE",
                    "WFR",
                    "GFR",
                    "ALQ",
                    "TAB",
                    "VFP_TYPE",
                    "TABLE_NUMBER",
                    "DATUM",
                    "RATE_TYPE",
                    "WFR_TYPE",
                    "GFR_TYPE",
                    "ALQ_TYPE",
                    "PRESSURE_TYPE",
                    "TAB_TYPE",
                    "UNIT_TYPE",
                ],
                data=[
                    [
                        50000.0,
                        40.0,
                        0.0,
                        500.0,
                        0.0,
                        100.0,
                        "VFPPROD",
                        1,
                        3000.0,
                        "GAS",
                        "WGR",
                        "GOR",
                        "''",
                        "THP",
                        "BHP",
                        "METRIC",
                    ]
                ],
            ),
            pd.DataFrame(
                columns=[
                    "RATE",
                    "PRESSURE",
                    "WFR",
                    "GFR",
                    "ALQ",
                    "TAB",
                    "VFP_TYPE",
                    "TABLE_NUMBER",
                    "DATUM",
                    "RATE_TYPE",
                    "WFR_TYPE",
                    "GFR_TYPE",
                    "ALQ_TYPE",
                    "PRESSURE_TYPE",
                    "TAB_TYPE",
                    "UNIT_TYPE",
                ],
                data=[
                    [
                        10000.0,
                        10.0,
                        0.0,
                        50.0,
                        0.0,
                        200.0,
                        "VFPPROD",
                        2,
                        4000.0,
                        "GAS",
                        "WGR",
                        "GOR",
                        "''",
                        "THP",
                        "BHP",
                        "METRIC",
                    ]
                ],
            ),
            pd.DataFrame(
                columns=[
                    "RATE",
                    "PRESSURE",
                    "TAB",
                    "VFP_TYPE",
                    "TABLE_NUMBER",
                    "DATUM",
                    "RATE_TYPE",
                    "PRESSURE_TYPE",
                    "TAB_TYPE",
                    "UNIT_TYPE",
                ],
                data=[
                    [
                        50000.0,
                        100.0,
                        200.0,
                        "VFPINJ",
                        3,
                        3200.0,
                        "GAS",
                        "THP",
                        "BHP",
                        "METRIC",
                    ],
                ],
            ),
            pd.DataFrame(
                columns=[
                    "RATE",
                    "PRESSURE",
                    "TAB",
                    "VFP_TYPE",
                    "TABLE_NUMBER",
                    "DATUM",
                    "RATE_TYPE",
                    "PRESSURE_TYPE",
                    "TAB_TYPE",
                    "UNIT_TYPE",
                ],
                data=[
                    [
                        50000.0,
                        100.0,
                        200.0,
                        "VFPINJ",
                        4,
                        3200.0,
                        "GAS",
                        "THP",
                        "BHP",
                        "METRIC",
                    ],
                ],
            ),
        ],
    ),
]


@pytest.mark.parametrize("test_input, expected", VFPPROD_CASES)
def test_res2df_vfpprod(test_input, expected):
    """Test res2df for VFPPROD"""
    deck = ResdataFiles.str2deck(test_input)
    vfpdf = vfp.df(deck, "VFPPROD")

    pd.testing.assert_frame_equal(vfpdf, expected)


@pytest.mark.parametrize("test_input, expected", VFPPROD_CASES)
def test_res2pyarrow_vfpprod(test_input, expected):
    """Test res2pyarrow for VFPPROD"""
    deck = ResdataFiles.str2deck(test_input)
    # Read first into pyarrow tables
    vfppa = vfp.pyarrow_tables(deck, "VFPPROD")
    # Convert pyarrow table to basic data types for VFPPROD
    vfpprod_data = vfp.pyarrow2basic_data(vfppa[0])
    # Convert basic data types to res2df DataFrame for VFPPROD
    vfpdf = vfp.basic_data2df(vfpprod_data)

    # Check that all steps lead to desired end result
    pd.testing.assert_frame_equal(vfpdf, expected)


@pytest.mark.parametrize("test_input, expected", [VFPPROD_CASES[0]])
def test_df2res_vfpprod(test_input, expected):
    """Test df2res for VFPPROD (case without default values)"""
    ecl_vfpprod = vfp.df2res(expected, "VFPPROD")

    assert ecl_vfpprod.strip() == test_input.strip()


@pytest.mark.parametrize("test_input, expected", [VFPPROD_CASES[0]])
def test_pyarrow2ecl_vfpprod(test_input, expected):
    """Test pyarrow2ecl for VFPPROD (case without default values)"""
    deck = ResdataFiles.str2deck(vfp.df2res(expected, "VFPPROD"))
    vfpprod_df = vfp.df(deck, "VFPPROD")
    vfpprod_data = vfp.df2basic_data(vfpprod_df)
    vfpprod_pa = vfp.basic_data2pyarrow(vfpprod_data)
    vfpprod_data = vfp.pyarrow2basic_data(vfpprod_pa)
    vfpprod_df = vfp.basic_data2df(vfpprod_data)
    vfpprod_ecl = vfp.df2res(vfpprod_df, "VFPPROD")

    assert vfpprod_ecl.strip() == test_input.strip()


@pytest.mark.parametrize("test_input, expected", VFPINJ_CASES)
def test_res2df_vfpinj(test_input, expected):
    """Test res2df for VFPINJ"""
    deck = ResdataFiles.str2deck(test_input)
    vfpdf = vfp.df(deck, "VFPINJ")

    pd.testing.assert_frame_equal(vfpdf, expected)


@pytest.mark.parametrize("test_input, expected", [VFPINJ_CASES[0]])
def test_df2res_vfpinj(test_input, expected):
    """Test df2res for VFPINJ (case without default values)"""
    ecl_vfpinj = vfp.df2res(expected, "VFPINJ")

    assert ecl_vfpinj.strip() == test_input.strip()


@pytest.mark.parametrize("test_input, expected", [VFPINJ_CASES[0]])
def test_pyarrow2ecl_vfpinj(test_input, expected):
    """Test pyarrow2ecl for VFPPROD (case without default values)"""
    deck = ResdataFiles.str2deck(vfp.df2res(expected, "VFPINJ"))
    vfpinj_df = vfp.df(deck, "VFPINJ")
    vfpinj_data = vfp.df2basic_data(vfpinj_df)
    vfpinj_pa = vfp.basic_data2pyarrow(vfpinj_data)
    vfpinj_data = vfp.pyarrow2basic_data(vfpinj_pa)
    vfpinj_df = vfp.basic_data2df(vfpinj_data)
    vfpinj_ecl = vfp.df2res(vfpinj_df, "VFPINJ")

    assert vfpinj_ecl.strip() == test_input.strip()


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_res2df_vfpprods(test_input, expected):
    """Test res2df for files with multiple VFPPROD"""
    deck = ResdataFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPPROD")

    # Two VFPPROD curves in file corresponding to curves 0 and 1
    for i, n in enumerate([0, 1]):
        pd.testing.assert_frame_equal(vfpdfs[i], expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_res2pyarrow_vfpprods(test_input, expected):
    """Test res2df with pyarrow for files with multiple VFPPROD"""
    deck = ResdataFiles.str2deck(test_input)
    vfppas = vfp.pyarrow_tables(deck, "VFPPROD")

    # Two VFPPROD curves in file corresponding to curves 0 and 1
    for i, n in enumerate([0, 1]):
        vfpprod_data = vfp.pyarrow2basic_data(vfppas[i])
        vfpdf = vfp.basic_data2df(vfpprod_data)
        pd.testing.assert_frame_equal(vfpdf, expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_res2df_vfpinjs(test_input, expected):
    """Test res2df for files with multiple VFPINJ"""
    deck = ResdataFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPINJ")

    # Two VFPINJ curves in file corresponding to curves 2 and 3
    for i, n in enumerate([2, 3]):
        pd.testing.assert_frame_equal(vfpdfs[i], expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_eclpyarrow_vfpinjs(test_input, expected):
    """Test res2df for pyarrow for files with multiple VFPINJ"""
    deck = ResdataFiles.str2deck(test_input)
    vfppas = vfp.pyarrow_tables(deck, "VFPINJ")

    # Two VFPINJ curves in file corresponding to curves 2 and 3
    for i, n in enumerate([2, 3]):
        vfpinj_data = vfp.pyarrow2basic_data(vfppas[i])
        vfpdf = vfp.basic_data2df(vfpinj_data)
        pd.testing.assert_frame_equal(vfpdf, expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_res2df_vfpprod_no(test_input, expected):
    """Test res2df for files with multiple VFPPROD with vfp number argument"""
    deck = ResdataFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPPROD", "2")

    # VFPPROD curve with VFP number 2 is curve 1 in file
    pd.testing.assert_frame_equal(vfpdfs[0], expected[1])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_res2pyarrow_vfpprod_no(test_input, expected):
    """Test res2df for pyarrow for files with multiple
    VFPPROD with vfp number argument
    """
    deck = ResdataFiles.str2deck(test_input)
    vfppas = vfp.pyarrow_tables(deck, "VFPPROD", "2")
    vfpprod_data = vfp.pyarrow2basic_data(vfppas[0])
    vfpdf = vfp.basic_data2df(vfpprod_data)

    # VFPPROD curve with VFP number 2 is curve 1 in file
    pd.testing.assert_frame_equal(vfpdf, expected[1])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_res2df_vfpinj_no(test_input, expected):
    """Test res2df for files with multiple VFPINJ with vfp number argument"""
    deck = ResdataFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPINJ", "4")

    # VFPINJ curve with VFP number 4 is curve 3 in file
    pd.testing.assert_frame_equal(vfpdfs[0], expected[3])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_res2pyarrow_vfpinj_no(test_input, expected):
    """Test res2df for pyarrow files with multiple VFPINJ with vfp number argument"""
    deck = ResdataFiles.str2deck(test_input)
    vfppas = vfp.pyarrow_tables(deck, "VFPINJ", "4")

    vfpinj_data = vfp.pyarrow2basic_data(vfppas[0])
    vfpdf = vfp.basic_data2df(vfpinj_data)

    # VFPINJ curve with VFP number 4 is curve 3 in file
    pd.testing.assert_frame_equal(vfpdf, expected[3])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_res2df_vfpprods_no(test_input, expected):
    """Test res2df for files with multiple VFPPROD with vfp number argument as range"""
    deck = ResdataFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPPROD", "[1:2]")

    # VFPPROD curves with VFP numbers 1 and 2 are curves 0 and 1
    for i, n in enumerate([0, 1]):
        pd.testing.assert_frame_equal(vfpdfs[i], expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_res2pyarrow_vfpprods_no(test_input, expected):
    """Test res2df for pyarrow for files with multiple VFPPROD
    with vfp number argument as range
    """
    deck = ResdataFiles.str2deck(test_input)
    vfppas = vfp.pyarrow_tables(deck, "VFPPROD", "[1:2]")

    # VFPPROD curves with VFP numbers 1 and 2 are curves 0 and 1
    for i, n in enumerate([0, 1]):
        vfpprod_data = vfp.pyarrow2basic_data(vfppas[i])
        vfpdf = vfp.basic_data2df(vfpprod_data)
        pd.testing.assert_frame_equal(vfpdf, expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_res2df_vfpinjs_no(test_input, expected):
    """Test res2df for files with multiple VFPINJ with vfp number
    argument as range
    """
    deck = ResdataFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPINJ", "[3:4]")

    # VFPINJ curves with VFP numbers 3 and 4 are curves 2 and 3
    for i, n in enumerate([2, 3]):
        pd.testing.assert_frame_equal(vfpdfs[i], expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_res2pyarrow_vfpinjs_no(test_input, expected):
    """Test res2df for pyararow for files with multiple VFPINJ with vfp
    number argument as range
    """
    deck = ResdataFiles.str2deck(test_input)
    vfppas = vfp.pyarrow_tables(deck, "VFPINJ", "[3:4]")

    # VFPINJ curves with VFP numbers 3 and 4 are curves 2 and 3
    for i, n in enumerate([2, 3]):
        vfpinj_data = vfp.pyarrow2basic_data(vfppas[i])
        vfpdf = vfp.basic_data2df(vfpinj_data)
        pd.testing.assert_frame_equal(vfpdf, expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_basic_data_vfpprods_no(test_input, expected):
    """Test res2df basic_data reading for files with multiple VFPPROD
    with vfp number argument as range
    """
    deck = ResdataFiles.str2deck(test_input)
    basic_data_vfps = vfp.basic_data(deck, "VFPPROD", "[1:2]")

    # VFPPROD curves with VFP numbers 1 and 2 are curves 0 and 1
    for i, n in enumerate([0, 1]):
        df_vfp = vfp.basic_data2df(basic_data_vfps[i])
        pd.testing.assert_frame_equal(df_vfp, expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_basic_data_vfpinjs_no(test_input, expected):
    """Test res2df basic_data reading for files with multiple VFPINJ with vfp
    number argument as range
    """
    deck = ResdataFiles.str2deck(test_input)
    basic_data_vfps = vfp.basic_data(deck, "VFPINJ", "[3:4]")

    # VFPINJ curves with VFP numbers 3 and 4 are curves 2 and 3
    for i, n in enumerate([2, 3]):
        df_vfp = vfp.basic_data2df(basic_data_vfps[i])
        pd.testing.assert_frame_equal(df_vfp, expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_pyarrow2basic_data_vfpprods_no(test_input, expected):
    """Test res2df pyarrow2basic_data for files with multiple VFPPROD
    with vfp number argument as range
    """
    deck = ResdataFiles.str2deck(test_input)
    pyarrow_vfps = vfp.pyarrow_tables(deck, "VFPPROD", "[1:2]")

    # VFPPROD curves with VFP numbers 1 and 2 are curves 0 and 1
    for i, n in enumerate([0, 1]):
        basic_data_vfp = vfp.pyarrow2basic_data(pyarrow_vfps[i])
        df_vfp = vfp.basic_data2df(basic_data_vfp)
        pd.testing.assert_frame_equal(df_vfp, expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_pyarrow2basic_data_vfpinjs_no(test_input, expected):
    """Test res2df pyarrow2basic_data for files with multiple VFPINJ with vfp
    number argument as range
    """
    deck = ResdataFiles.str2deck(test_input)
    pyarrow_vfps = vfp.pyarrow_tables(deck, "VFPINJ", "[3:4]")

    # VFPINJ curves with VFP numbers 3 and 4 are curves 2 and 3
    for i, n in enumerate([2, 3]):
        basic_data_vfp = vfp.pyarrow2basic_data(pyarrow_vfps[i])
        df_vfp = vfp.basic_data2df(basic_data_vfp)
        pd.testing.assert_frame_equal(df_vfp, expected[n])


@pytest.fixture(scope="class", params=vfp._vfpprod.BASIC_DATA_KEYS)
def vfpprod_key(request):
    yield request.param


class Test_Exceptions_vfpprod_keys:
    @pytest.mark.parametrize("test_input, dummy", VFPPROD_CASES)
    def test_basic_data_key_exceptions_vfpprods(self, vfpprod_key, test_input, dummy):
        """Test exceptions for basic data format (not containing all
        required keywords) for VFPPROD"
        """
        deck = ResdataFiles.str2deck(test_input)
        basic_data_vfpprods = vfp.basic_data(deck, "VFPPROD")

        # Check if exception is raises if one key is missing
        basic_data_vfpprod_no_key = copy.deepcopy(basic_data_vfpprods[0])
        del basic_data_vfpprod_no_key[vfpprod_key]
        with pytest.raises(
            KeyError, match=f"{vfpprod_key} key is not in basic data dictionary VFPPROD"
        ):
            vfp._vfpprod._check_basic_data(basic_data_vfpprod_no_key)


@pytest.fixture(scope="class", params=VFPPROD_ARRAY_NAMES)
def vfpprod_array_name(request):
    print("\n SETUP", request.param)
    yield request.param
    # print("\n UNDO", request.param)


class Test_Exceptions_vfpprod_dims:
    @pytest.mark.parametrize("test_input, dummy", [VFPPROD_CASES[0]])
    def test_basic_data_array_dim_exceptions_vfpprods(
        self, vfpprod_array_name, test_input, dummy
    ):
        """Test exceptions for basic data format
        (inconsistency in array dimensions) for VFPPROD"
        """
        deck = ResdataFiles.str2deck(test_input)
        basic_data_vfpprods = vfp.basic_data(deck, "VFPPROD")

        # Check if exception is raises if array dimension is wrong
        basic_data_vfpprod_wrong_dim = copy.deepcopy(basic_data_vfpprods[0])
        basic_data_vfpprod_wrong_dim[vfpprod_array_name] = basic_data_vfpprod_wrong_dim[
            vfpprod_array_name
        ][1:]
        with pytest.raises(ValueError):
            vfp._vfpprod._check_basic_data(basic_data_vfpprod_wrong_dim)


@pytest.mark.parametrize("test_input, expected", VFPPROD_CASES)
def test_basic_data_dims_vfpprods(test_input, expected):
    """Test exceptions for dimensions consistency for basic data format
    (not containing all required keywords) for VFPPROD"
    """
    deck = ResdataFiles.str2deck(test_input)
    basic_data_vfpprods = vfp.basic_data(deck, "VFPPROD")

    # Check if exception is raised if dimensions are wrong
    basic_data_vfpprod = copy.deepcopy(basic_data_vfpprods[0])
    basic_data_vfpprod["THP_INDICES"] = basic_data_vfpprod["THP_INDICES"][1:]
    with pytest.raises(ValueError):
        vfp._vfpprod._check_basic_data(basic_data_vfpprod)


@pytest.fixture(scope="class", params=vfp._vfpinj.BASIC_DATA_KEYS)
def vfpinj_key(request):
    print("\n SETUP", request.param)
    yield request.param
    # print("\n UNDO", request.param)


class Test_Exceptions_vfpinj_keys:
    @pytest.mark.parametrize("test_input, dummy", VFPINJ_CASES)
    def test_basic_data_key_exceptions_vfpinjs(self, vfpinj_key, test_input, dummy):
        """Test exceptions for basic data format (not containing all
        required keywords) for VFPINJ"
        """
        deck = ResdataFiles.str2deck(test_input)
        basic_data_vfpinjs = vfp.basic_data(deck, "VFPINJ")

        # Check if exception is raises if one key is missing
        basic_data_vfpinj_no_key = copy.deepcopy(basic_data_vfpinjs[0])
        del basic_data_vfpinj_no_key[vfpinj_key]
        with pytest.raises(
            KeyError, match=f"{vfpinj_key} key is not in basic data dictionary VFPINJ"
        ):
            vfp._vfpinj._check_basic_data(basic_data_vfpinj_no_key)


@pytest.fixture(scope="class", params=VFPINJ_ARRAY_NAMES)
def vfpinj_array_name(request):
    print("\n SETUP", request.param)
    yield request.param
    # print("\n UNDO", request.param)


class Test_Exceptions_vfpinj_dims:
    @pytest.mark.parametrize("test_input, dummy", [VFPINJ_CASES[0]])
    def test_basic_data_array_dim_exceptions_vfpinjs(
        self, vfpinj_array_name, test_input, dummy
    ):
        """Test exceptions for basic data format
        (inconsistency in array dimensions) for VFPINJ"
        """
        deck = ResdataFiles.str2deck(test_input)
        basic_data_vfpinjs = vfp.basic_data(deck, "VFPINJ")

        # Check if exception is raises if array dimension if wrong
        basic_data_vfpinj_wrong_dim = copy.deepcopy(basic_data_vfpinjs[0])
        basic_data_vfpinj_wrong_dim[vfpinj_array_name] = basic_data_vfpinj_wrong_dim[
            vfpinj_array_name
        ][1:]
        with pytest.raises(ValueError):
            vfp._vfpinj._check_basic_data(basic_data_vfpinj_wrong_dim)
