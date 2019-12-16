# -*- coding: utf-8 -*-
"""Converter module for Eclipse RFT output files to Pandas Dataframes

If MULTISEG wells are found, the segment data associated to
a connection is merged onto the same row as additional columns,
assuming connections do not point to more than one segment.

If ICD segments are detected (recognized as branches only containing
one segment), they are merged into the same row that already contains
connection data (CONxxxxx) and its segment data (now giving
information for the conditions in the tubing).

The columns representing SEGxxxxx data on ICD segments are renamed
by adding the prefix ``ICD_``
"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import datetime
import argparse
import logging

import numpy as np
import pandas as pd

from .eclfiles import EclFiles
from .common import merge_zones

# logging.basicConfig(level=logging.DEBUG)


def _rftrecords2df(eclfiles):
    """Construct a dataframe just for navigation on the RFT records.
    """
    rftfile = eclfiles.get_rftfile()
    rftrecords = pd.DataFrame(rftfile.headers)
    rftrecords.columns = ["recordname", "recordlength", "recordtype"]
    rftrecords["timeindex"] = np.nan
    # the TIME record signifies that the forthcoming records belong to
    # this TIME value, and we make a new column in the header data that
    # tells us the row number for the associated TIME record
    rftrecords.loc[rftrecords["recordname"] == "TIME", "timeindex"] = rftrecords[
        rftrecords["recordname"] == "TIME"
    ].index
    rftrecords.fillna(
        method="ffill", inplace=True
    )  # forward fill (because any record is associated to the previous TIME record)
    rftrecords["timeindex"] = rftrecords["timeindex"].astype(int)
    logging.info(
        "Located %s RFT records at %s distinct dates",
        str(len(rftrecords)),
        str(len(rftrecords["timeindex"].unique())),
    )
    return rftrecords


def rft2df(eclfiles):
    """Construct the final dataframe of RFT data"""
    rftrecords = _rftrecords2df(eclfiles)
    rftfile = eclfiles.get_rftfile()

    # This will be our end-product, all CONxxxxx data and SEGxxxxx
    # data merged appropriately together.  Index will be (date,
    # wellname, connection index) rolled out.
    rftdata = pd.DataFrame()

    # Loop over the TIME records and its associated data:
    for timerecordidx in rftrecords["timeindex"].unique():

        # Pick out the headers (with row indices) for the data
        # relevant to this TIME record:
        headers = rftrecords[rftrecords["timeindex"] == timerecordidx]

        dateidx = int(headers[headers.recordname == "DATE"].index.values)
        welletcidx = int(headers[headers.recordname == "WELLETC"].index.values)

        date = datetime.date(
            rftfile[dateidx][2], rftfile[dateidx][1], rftfile[dateidx][0]
        )
        well = rftfile[welletcidx][1].strip()
        wellmodel = rftfile[welletcidx][6].strip()  # MULTISEG or STANDARD

        logging.info(
            "Extracting {} well {:>8} at {}, record index: {}".format(
                wellmodel, well, date, timerecordidx
            )
        )

        # Collect all the headers that have the same length as 'DEPTH'
        # (we could pick most others as well) This will be the number
        # of cells that have data associated and we use this to
        # safeguard that we do not make a non-rectangular dataset (by
        # picking some datatype that does not refer to connections)

        numberofrows = headers[headers.recordname == "DEPTH"]["recordlength"]
        if not numberofrows.empty:
            numberofrows = int(numberofrows)
        else:
            logging.debug("Well %s has no data to extract at %s", str(well), str(date))
            continue

        # These datatypes now align nicely into a matrix of numbers,
        # so we extract them into a pandas DataFrame
        con_headers = headers[headers.recordlength == numberofrows].recordname

        # Temporary dataset for this (date, wellname) record,
        # identified by timerecordidx
        con_data = pd.DataFrame()
        # Loop over the con_headers:
        for rftidx, recordname in con_headers.iteritems():
            # Extract CON-data and put it into the con_data
            con_data[recordname] = list(rftfile[rftidx])

        con_data["CONIDX"] = con_data.index + 1  # Add an index that starts with 1

        # Set branch count to 1. If it is a multisegment well, this
        # variable might get updated.
        numberofbranches = 1

        # Process multisegment data (not necessarily the same number
        # of rows as the connection data) Currently data for segments
        # that are not associated with a connection will not be
        # included.

        # Ignore if wellmodel says MULTISEG but we cannot find any
        # SEGxxxxx data in the record.
        if (
            wellmodel == "MULTISEG"
            and not headers[headers["recordname"].str.startswith("SEG")].empty
        ):
            logging.debug("Well %s is MULTISEG but has no SEG data", well)
            numberofrows = int(
                headers[headers["recordname"] == "SEGDEPTH"]["recordlength"]
            )
            seg_headers = headers[
                (headers["recordname"].str.startswith("SEG"))
                & (headers["recordlength"] == numberofrows)
            ].recordname

            seg_data = pd.DataFrame()
            # Loop over SEGheaders:
            for rftidx, recordname in seg_headers.iteritems():
                seg_data[recordname] = list(rftfile[rftidx])

            seg_data["SEGIDX"] = seg_data.index + 1  # Add an index that starts with 1

            # Determine well topology: The way ICDs are modelled
            # complexifies this, as each ICD device must be put on a
            # branch SEGNXT must be used for this, it points to the
            # next segment downstream.  The next segment upsteam is
            # not well defined (it can point to many segments)

            # Leaf segments are those segments with no upstream
            # segment Merge SEGIDX and SEGNXT, leaf segments now have
            # NaN for SEGIDX_y after the merge:
            merged_seg_data = pd.merge(
                seg_data, seg_data, how="outer", left_on="SEGIDX", right_on="SEGNXT"
            )
            # We may compute leafsegments like this:
            # leafsegments = merged_seg_ata[merged_seg_data["SEGIDX_y"] == numpy.nan]

            # After having removed leaf segments, we can claim that
            # the maximum value of SEGBRNO determines the number of
            # well branches. This will fail if ICD segments are
            # connected in a series, if you have such a setup, you are
            # on your own (it will probably just be recognized as an
            # extra branch)

            numberofbranches = int(
                merged_seg_data[~merged_seg_data["SEGIDX_y"].isnull()][
                    "SEGBRNO_x"
                ].max()
            )

            # After-note:
            # An equivalent implementation could be to do such
            # a filter: SEGDATA.groupby('SEGBRNO').count() == 1

            # Now we can test if we have any ICD segments, that is the
            # case if we have any segments that have SEGBRNO higher than
            # the branch count
            icd_present = seg_data["SEGBRNO"].max() > numberofbranches

            if icd_present:
                icd_seg_data = seg_data[seg_data["SEGBRNO"] > numberofbranches]
                # Chop away the icd's from the seg_data dataframe:
                seg_data = seg_data[seg_data["SEGBRNO"] <= numberofbranches]

                # Rename columns in icd dataset:
                icd_seg_data.columns = ["ICD_" + x for x in icd_seg_data.columns]

                # Merge ICD segments to the CONxxxxx data. We will be
                # connection-centric in the outputted rows, that is
                # one row pr. connection. If the setup is with more
                # than one segment pr. connection (e.g. reservoir
                # cell), then we would have to be smarter. Either
                # averaging the properties, or be segment-centric in
                # the output.
                #
                # Petrel happily puts many ICD segments to the same
                # connection. This setup is a bug, with partially
                # unknown effects when simulated in Eclipse Should we
                # warn the user??

                con_icd_data = pd.merge(
                    con_data, icd_seg_data, right_on="ICD_SEGBRNO", left_on="CONBRNO"
                )

                # Merge SEGxxxxx to icd_conf_data
                conseg_data = pd.merge(
                    con_icd_data, seg_data, left_on="ICD_SEGNXT", right_on="SEGIDX"
                )

                # Add more data:
                conseg_data["CompletionDP"] = 0
                nonzero_pres = (conseg_data["CONPRES"] > 0) & (
                    conseg_data["SEGPRES"] > 0
                )
                conseg_data.loc[nonzero_pres, "CompletionDP"] = (
                    conseg_data[nonzero_pres]["CONPRES"]
                    - conseg_data[nonzero_pres]["SEGPRES"]
                )

            if not icd_present:

                # Merge SEGxxxxx to CONxxxxx data if we can find data that match them
                if "CONSEGNO" in con_data and "SEGIDX" in seg_data:
                    conseg_data = pd.merge(
                        con_data, seg_data, left_on="CONSEGNO", right_on="SEGIDX"
                    )
                else:
                    # Give up, you will get to distinct blocks in your CSV file when we
                    conseg_data = pd.concat([con_data, seg_data], sort=True)

            # Overwrite the con_data structure with the augmented data
            # structure including segments and potential ICD.
            con_data = conseg_data
        con_data["DRAWDOWN"] = 0  # Set a default so that the column always exists
        if (
            "CONPRES" in con_data.columns
        ):  # Only try to calculate this if CONPRES is actually nonzero.
            con_data.loc[con_data.CONPRES > 0, "DRAWDOWN"] = (
                con_data[con_data.CONPRES > 0]["PRESSURE"]
                - con_data[con_data.CONPRES > 0]["CONPRES"]
            )

        con_data["DATE"] = str(date)
        con_data["WELL"] = well
        con_data["WELLMODEL"] = wellmodel

        # Replicate S3Graf calculated data:
        if "PRESSURE" in con_data.columns:
            con_data["CONBPRES"] = con_data["PRESSURE"]  # Just an alias
        if "CONLENEN" in con_data.columns and "CONLENST" in con_data.columns:
            con_data["CONMD"] = 0.5 * (con_data.CONLENST + con_data.CONLENEN)
            con_data["CONLENTH"] = con_data.CONLENEN - con_data.CONLENST

        if "CONORAT" in con_data.columns and "CONLENTH" in con_data.columns:
            con_data["CONORATS"] = con_data.CONORAT / con_data.CONLENTH
            con_data["CONWRATS"] = con_data.CONWRAT / con_data.CONLENTH
            con_data["CONGRATS"] = con_data.CONGRAT / con_data.CONLENTH

        rftdata = rftdata.append(con_data, ignore_index=True, sort=False)

    # Fill empty cells with zeros. This is to avoid Spotfire
    # interpreting columns with numbers as strings. An alternative
    # solution that keeps NaN would be to add a second row in the
    # output containing the datatype
    rftdata.fillna(0, inplace=True)

    # The HOSTGRID data seems often to be empty, check if it is and delete if so:
    if "HOSTGRID" in rftdata.columns:
        if len(rftdata.HOSTGRID.unique()) == 1:
            if rftdata.HOSTGRID.unique()[0].strip() == "":
                del rftdata["HOSTGRID"]

    zonemap = eclfiles.get_zonemap()
    if zonemap:
        if "K" in rftdata:
            kname = "K"
        else:
            kname = "CONKPOS"
        rftdata = merge_zones(rftdata, zonemap, kname=kname)

    return rftdata


# Remaining functions are for the command line interface


def fill_parser(parser):
    """Set up sys.argv parsers.

    Arguments:
        parser (argparse.ArgumentParser or argparse.subparser): parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE",
        help=(
            "Name of Eclipse DATA file or RFT file. "
            "If DATA file is provided, it will look for"
            " the associated DATA file"
        ),
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Name of output CSV file.", default="rft.csv"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def main():
    """Entry-point for module, for command line utility
    """
    logging.warning("rft2csv is deprecated, use 'ecl2csv rft <args>' instead")
    parser = argparse.ArgumentParser()
    parser = fill_parser(parser)
    args = parser.parse_args()
    rft2df_main(args)


def rft2df_main(args):
    """Entry-point for module, for command line utility"""
    if args.verbose:
        logging.basicConfig()
        logging.getLogger().setLevel(logging.INFO)
    if args.DATAFILE.endswith(".RFT"):
        # Support the RFT file as an argument also:
        eclfiles = EclFiles(args.DATAFILE.replace(".RFT", "") + ".DATA")
    else:
        eclfiles = EclFiles(args.DATAFILE)
    rft_df = rft2df(eclfiles)
    rft_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)


def df(eclfiles):
    """Main function for Python API users"""
    return rft2df(eclfiles)


## Vector	Description
## CONDEPTH	Depth at the centre of each connection in the well
## CONLENST	Length down the tubing from the BH reference
##              point to the start of the connection
## CONLENEN	Length down the tubing from the BH reference point to the
##              far end of the connection
## CONPRES	Pressure in the wellbore at the connection
## CONORAT	Oil production rate of the connection at surface conditions
## CONWRAT	Water production rate of the connection at surface conditions
## CONGRAT	Gas production rate of the connection at surface conditions
## CONOTUB	Oil flow rate through the tubing at the start of the
##              connection at surface conditions
## CONWTUB	Water flow rate through the tubing at the start of the
##              connection at surface conditions
## CONGTUB	Gas flow rate through the tubing at the start of the
##              connection at surface conditions
## CONVTUB	Volumetric flow rate of the mixture at the start of the connection
## CONFAC	Connection transmissibility factor
## CONKH	Connection Kh value
## CONNXT	Number of the neighbouring connection towards the wellhead
## CONSEGNO	Segment number containing the connection
## CONBRNO	Branch number containing the connection
## CONIPOS	I location of the connection
## CONJPOS	J location of the connection
## CONKPOS	K location of the connection
## CONBDEPH	Depth of the grid block of the connection
## CONBPRES	Pressure of the grid block of the connection
##              (Copy of the PRESSURE data)
## CONBSWAT	Water saturation of the grid block of the connection
## CONBSGAS	Gas saturation of the grid block of the connection
## CONBSOIL	Oil saturation of the grid block of the connection
## COMPLETION	Completion index of the connection
##
## The above values are taken from the corresponding RFT data.
##
## Vector	Description
## CONMD	Measured depth of the connection
## CONLENTH	Length of the connection
## CONORATS	Scaled oil production rate at surface conditions
## CONWRATS	Scaled water production rate at surface conditions
## CONGRATS	Scaled gas production rate at surface conditions
##
##
## Vector	Description
## SEGDEPTH	Depth at the far end of each segment
## SEGLENST	Length down the tubing from the zero tubing length
##              reference point to the start of the segment
## SEGLELEN	Length down the tubing from the zero tubing length
##              reference point to the far end of the segment
## SEGXCORD	X-coordinate at the far end of the segment
##              (as entered by the 11th item of the WELSEGS record)
## SEGXCORD	Y-coordinate at the far end of the segment
##              (as entered by the 12th item of the WELSEGS record)
## SEGPRES	Pressure in the wellbore at the far end of the segment
## SEGORAT	Oil flow rate through the segment through its near end
## SEGWRAT	Water flow rate through the segment through its near end
## SEGGRAT	Gas flow rate through the segment through its near end
## SEGOVEL	Free oil phase velocity through the segment
## SEGWVEL	Water flow velocity through the segment
## SEGGVEL	Free gas phase flow velocity through the segment
## SEGOHF	Free oil phase holdup fraction in the segment
## SEGWHF	Water holdup fraction in the segment
## SEGGHF	Free gas phase holdup fraction in the segment
## SEGBRNO	Branch number of the segment
## SEGNXT	Number of the neighbouring segment towards the wellhead
##
## As for the plt data S3GRAF calculate some additional vectors for the segment data.
##
## Vector	Description
## SEGMD	Segment measured depth
## SEGLENTH	Segment length
## SEGORATS	Scaled water flow rate through the segment
## SEGWRATS	Scaled  water flow rate through the segment
## SEGGRATS	Scaled gas flow rate through the segment
## SEGCORAT	Summed connection oil flow rate through segment
## SEGCWRAT	Summed connection water flow rate through segment
## SEGCGRAT	Summer connection gas flow rate through segment
## SEGCORTS	Scaled summed connection oil flow rate through segment
## SEGCWRTS	Scaled summed connection water flow rate through segment
## SEGCGRTS	Scaled summed connection gas flow rate through segment
