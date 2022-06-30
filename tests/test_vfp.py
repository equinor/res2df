import pandas as pd
import pytest

from ecl2df import EclFiles, vfp

try:
    import opm  # noqa
except ImportError:
    pytest.skip(
        "OPM is not installed",
        allow_module_level=True,
    )

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
     50000    500000     5e+06 /

-- THP units - barsa ( 2 values )
        40       100 /

-- WGR units - sm3/sm3 ( 2 values )
         0     1e-05 /

-- GOR units - sm3/sm3 ( 2 values )
       500      4000 /

-- '' units -  ( 1 values )
         0 /

 1  1  1  1    160.11    130.21    180.31
/
 1  1  2  1    140.12    110.22    160.32
/
 1  2  1  1    165.13    135.23    185.33
/
 1  2  2  1    145.14    115.24    165.34
/
 2  1  1  1    240.15    210.25    260.35
/
 2  1  2  1    220.16    190.26    240.36
/
 2  2  1  1    245.17    215.27    265.37
/
 2  2  2  1    225.18    195.28    245.38
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
     50000    500000     5e+06 /

-- THP units - barsa ( 2 values )
       100       200 /

 1    180.11    170.21    150.31
/
 2    270.12    260.22    240.32
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
def test_ecl2df_vfpprod(test_input, expected):
    """Test ecl2df for VFPPROD"""
    deck = EclFiles.str2deck(test_input)
    vfpdf = vfp.df(deck, "VFPPROD")

    pd.testing.assert_frame_equal(vfpdf, expected)


@pytest.mark.parametrize("test_input, expected", [VFPPROD_CASES[0]])
def test_df2ecl_vfpprod(test_input, expected):
    """Test df2ecl for VFPPROD (case without default values)"""
    ecl_vfpprod = vfp.df2ecl_vfpprod(expected)

    assert ecl_vfpprod.strip() == test_input.strip()


@pytest.mark.parametrize("test_input, expected", VFPINJ_CASES)
def test_ecl2df_vfpinj(test_input, expected):
    """Test ecl2df for VFPINJ"""
    deck = EclFiles.str2deck(test_input)
    vfpdf = vfp.df(deck, "VFPINJ")

    pd.testing.assert_frame_equal(vfpdf, expected)


@pytest.mark.parametrize("test_input, expected", [VFPINJ_CASES[0]])
def test_df2ecl_vfpinj(test_input, expected):
    """Test df2ecl for VFPINJ (case without default values)"""
    ecl_vfpinj = vfp.df2ecl_vfpinj(expected)

    assert ecl_vfpinj.strip() == test_input.strip()


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_ecl2df_vfpprods(test_input, expected):
    """Test ecl2df for files with multiple VFPPROD"""
    deck = EclFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPPROD")

    # Two VFPPROD curves in file corresponding to curves 0 and 1
    for i, n in enumerate([0, 1]):
        pd.testing.assert_frame_equal(vfpdfs[i], expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_ecl2df_vfpinjs(test_input, expected):
    """Test ecl2df for files with multiple VFPINJ"""
    deck = EclFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPINJ")

    # Two VFPINJ curves in file corresponding to curves 2 and 3
    for i, n in enumerate([2, 3]):
        pd.testing.assert_frame_equal(vfpdfs[i], expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_ecl2df_vfpprod_no(test_input, expected):
    """Test ecl2df for files with multiple VFPPROD with vfp number argument"""
    deck = EclFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPPROD", "2")

    # VFPPROD curve with VFP number 2 is curve 1 in file
    pd.testing.assert_frame_equal(vfpdfs[0], expected[1])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_ecl2df_vfpinj_no(test_input, expected):
    """Test ecl2df for files with multiple VFPINJ with vfp number argument"""
    deck = EclFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPINJ", "4")

    # VFPINJ curve with VFP number 4 is curve 3 in file
    pd.testing.assert_frame_equal(vfpdfs[0], expected[3])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_ecl2df_vfpprods_no(test_input, expected):
    """Test ecl2df for files with multiple VFPPROD with vfp number argument as range"""
    deck = EclFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPPROD", "[1:2]")

    # VFPPROD curves with VFP numbers 1 and 2 are curves 0 and 1
    for i, n in enumerate([0, 1]):
        pd.testing.assert_frame_equal(vfpdfs[i], expected[n])


@pytest.mark.parametrize("test_input, expected", MULTIPLE_VFP_CASES)
def test_ecl2df_vfpinjs_no(test_input, expected):
    """Test ecl2df for files with multiple VFPINJ with vfp number argument as range"""
    deck = EclFiles.str2deck(test_input)
    vfpdfs = vfp.dfs(deck, "VFPINJ", "[3:4]")

    # VFPINJ curves with VFP numbers 3 and 4 are curves 2 and 3
    for i, n in enumerate([2, 3]):
        pd.testing.assert_frame_equal(vfpdfs[i], expected[n])
