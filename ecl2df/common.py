"""
Common functions for ecl2df modules
"""


def parse_ecl_month(eclmonth):
    eclmonth2num = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "JLY": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }
    return eclmonth2num[eclmonth]
