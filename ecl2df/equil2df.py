#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract EQUIL from an Eclipse deck as Pandas DataFrame

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import argparse
import pandas as pd

from .eclfiles import EclFiles


def deck2equildf(deck):
    """Extract the data in the EQUIL keyword as a Pandas
    DataFrame.

    How each data value in the EQUIL records are to be interpreted
    depends on the phase configuration in the deck, which means
    that we need more than the EQUIL section alone to determine the
    dataframe.

    Return:
        pd.DataFrame
    """
    phasecount = sum(["OIL" in deck, "GAS" in deck, "WATER" in deck])
    if "OIL" in deck and "GAS" in deck and "WATER" in deck:
        # oil-water-gas
        columnnames = [
            "DATUM",
            "PRESSURE",
            "OWC",
            "PCOWC",
            "GOC",
            "PCGOC",
            "INITRS",
            "INITRV",
            "ACCURACY",
        ]
    if "OIL" not in deck and "GAS" in deck and "WATER" in deck:
        # gas-water
        columnnames = [
            "DATUM",
            "PRESSURE",
            "GWC",
            "PCGWC",
            "IGNORE1",
            "IGNORE2",
            "IGNORE3",
            "IGNORE4",
            "ACCURACY",
        ]
    if "OIL" in deck and "GAS" not in deck and "WATER" in deck:
        # oil-water
        columnnames = [
            "DATUM",
            "PRESSURE",
            "OWC",
            "PCOWC",
            "IGNORE1",
            "IGNORE2",
            "IGNORE3",
            "IGNORE4",
            "ACCURACY",
        ]
    if "OIL" in deck and "GAS" in deck and "WATER" not in deck:
        # oil-gas
        columnnames = [
            "DATUM",
            "PRESSURE",
            "IGNORE1",
            "IGNORE2",
            "GOC",
            "PCGOC",
            "IGNORE3",
            "IGNORE4",
            "ACCURACY",
        ]
    if phasecount == 1:
        columnnames = ["DATUM", "PRESSURE"]
    if not columnnames:
        raise ValueError("Unsupported phase configuration")

    if "EQUIL" not in deck:
        return pd.DataFrame

    records = []
    for rec in deck["EQUIL"]:
        rowlist = [x[0] for x in rec]
        if len(rowlist) > len(columnnames):
            rowlist = rowlist[: len(columnnames)]
            print(
                "WARNING: Something wrong with columnnames "
                + "or EQUIL-data, data is chopped!"
            )
        records.append(rowlist)

    df = pd.DataFrame(columns=columnnames, data=records)

    # The column handling can be made prettier..
    for col in df.columns:
        if "IGNORE" in col:
            del df[col]

    return df


def parse_args():
    """Parse sys.argv using argparse"""
    parser = argparse.ArgumentParser()
    parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument(
        "-o", "--output", type=str, help="Name of output csv file.", default="equil.csv"
    )
    return parser.parse_args()


def main():
    """Entry-point for module, for command line utility"""
    args = parse_args()
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    equil_df = deck2equildf(deck)
    equil_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)
