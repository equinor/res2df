""" Module with interface for ecl2df to VFPPROD and VFPINJ
keywords in Eclipse.
"""
from ._vfp import (  # noqa F:401
    basic_data,
    basic_data2df,
    basic_data2pyarrow,
    df,
    df2basic_data,
    df2ecl,
    df2ecls,
    dfs,
    fill_parser,
    fill_reverse_parser,
    pyarrow2basic_data,
    pyarrow_tables,
    vfp_main,
    vfp_reverse_main,
)
