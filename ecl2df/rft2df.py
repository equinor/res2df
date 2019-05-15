# -*- coding: utf-8 -*-
"""
Converter module for Eclipse RFT output files to Pandas Dataframes

If MULTISEG wells are found, the segment data associated to
a connection is merged onto the same row as additional columns,
assuming connections do not point to more than one segment.

If ICD segments are detected (recognized as branches only
containing one segment), they are merged into the same row that
already contains connection data (CONxxxxx) and its segment data
(now giving information for the conditions in the tubing).

The columns representing SEGxxxxx data on ICD segments are renamed
by adding the prefix 'ICD_'
"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import datetime
import argparse

import numpy as np
import pandas as pd

from .eclfiles import EclFiles


def rftrecords2df(eclfiles):
    """Pandas dataframe used to navigate in the RFT records in the file (not the data itself):"""
    rftfile = eclfiles.get_rftfile()
    rftrecords = pd.DataFrame(rftfile.headers)
    rftrecords.columns = ["recordname", "recordlength", "recordtype"]
    rftrecords["timeindex"] = np.nan
    # the TIME record signifies that the forthcoming records belong to
    # this TIME value, and we make a new column in the header data that
    # tells us the row number for the associated TIME record
    rftrecords.loc[rftrecords.recordname == "TIME", "timeindex"] = rftrecords[
        rftrecords.recordname == "TIME"
    ].index
    rftrecords.fillna(
        method="ffill", inplace=True
    )  # forward fill (because any record is associated to the previous TIME record)
    return rftrecords


def rft2df(eclfiles):
    rftrecords = rftrecords2df(eclfiles)
    rftfile = eclfiles.get_rftfile()
    # This will be our end-product, all CONxxxxx data and SEGxxxxx data merged appropriately together.
    # Index will be (date, wellname, connection index) rolled out.
    rftdata = pd.DataFrame()

    # Now loop over the TIME records and its associated data:
    for timerecordidx in rftrecords.timeindex.astype(int).unique():

        # Pick out the headers (with row indices) for the data relevant to this TIME record:
        headers = rftrecords[rftrecords["timeindex"] == timerecordidx]

        dateidx = int(headers[headers.recordname == "DATE"].index.values)
        welletcidx = int(headers[headers.recordname == "WELLETC"].index.values)

        date = datetime.date(
            rftfile[dateidx][2], rftfile[dateidx][1], rftfile[dateidx][0]
        )
        well = rftfile[welletcidx][1].strip()
        wellmodel = rftfile[welletcidx][6].strip()  # MULTISEG or STANDARD

        # print "Extracting", wellmodel, "well", str(well).ljust(8) + " at " +  str(date), "record index:", timerecordidx,

        # Collect all the headers that have the same length as 'DEPTH' (we could pick most others as well)
        # This will be the number of cells that have data associated and we use this to safeguard
        # that we do not make a non-rectangular dataset (by picking some datatype that does not refer
        # to connections)

        numberofrows = headers[headers.recordname == "DEPTH"]["recordlength"]
        if len(numberofrows):
            numberofrows = int(numberofrows)
            # print # just a newline to finish the print statememt above.
        else:
            # This can happen if the well is actually shut or stopped at this date.
            # print "(empty)"
            continue

        # These datatypes now align nicely into a matrix of numbers, so we extract them into a pandas DataFrame
        CONheaders = headers[headers.recordlength == numberofrows].recordname

        # Temporary dataset for this (date, wellname) record, identified by timerecordidx
        CONdata = pd.DataFrame()
        # Loop over the CONheaders:
        for rftidx, recordname in CONheaders.iteritems():
            # Extract CON-data and put it into the CONdata
            CONdata[recordname] = list(rftfile[rftidx])

        CONdata["CONIDX"] = CONdata.index + 1  # Add an index that starts with 1

        # Set branch count to 1. If it is a multisegment well, this variable might get updated.
        numberofbranches = 1

        # Process multisegment data (not necessarily the same number of rows as the connection data)
        # Currently data for segments that are not associated with a connection will not be included.

        # Ignore if wellmodel says MULTISEG but we cannot find any SEGxxxxx data in the record.
        if wellmodel == "MULTISEG" and len(
            headers[headers.recordname.str.startswith("SEG")]
        ):
            numberofrows = int(
                headers[headers.recordname == "SEGDEPTH"]["recordlength"]
            )
            SEGheaders = headers[
                (headers.recordname.str.startswith("SEG"))
                & (headers.recordlength == numberofrows)
            ].recordname

            SEGdata = pd.DataFrame()
            # Loop over SEGheaders:
            for rftidx, recordname in SEGheaders.iteritems():
                SEGdata[recordname] = list(rftfile[rftidx])

            SEGdata["SEGIDX"] = SEGdata.index + 1  # Add an index that starts with 1

            # Determine well topology:
            # The way ICDs are modelled complexifies this, as each ICD device must be put on a branch
            # SEGNXT must be used for this, it points to the next segment downstream
            # The next segment upsteam is not well defined (it can point to many segments)

            # Leaf segments are those segments with no upstream segment
            # Merge SEGIDX and SEGNXT, leaf segments now have NaN for SEGIDX_y after the merge:
            mergedSEGdata = pd.merge(
                SEGdata, SEGdata, how="outer", left_on="SEGIDX", right_on="SEGNXT"
            )
            leafsegments = mergedSEGdata[mergedSEGdata["SEGIDX_y"] == numpy.nan]

            # After having removed leaf segments, we can claim that the maximum value of SEGBRNO determines the
            # number of well branches. This will fail if ICD segments are connected in a series, if you
            # have such a setup, you are on your own (it will probably just be recognized as an extra branch)

            numberofbranches = int(
                mergedSEGdata[~mergedSEGdata["SEGIDX_y"].isnull()].SEGBRNO_x.max()
            )

            # After-note:
            # An equivalent implementation could be to do such a filter: SEGDATA.groupby('SEGBRNO').count() == 1

            # Now we can test if we have any ICD segments, that is the
            # case if we have any segments that have SEGBRNO higher than
            # the branch count
            icd_present = SEGdata.SEGBRNO.max() > numberofbranches

            if icd_present:
                icd_SEGdata = SEGdata[SEGdata.SEGBRNO > numberofbranches]
                # Chop away the icd's from the SEGdata dataframe:
                SEGdata = SEGdata[SEGdata.SEGBRNO <= numberofbranches]

                # Rename columns in icd dataset:
                icd_SEGdata.columns = ["ICD_" + x for x in icd_SEGdata.columns]

                # Merge ICD segments to the CONxxxxx data. We will be
                # connection-centric in the outputted rows, that is one
                # row pr. connection. If the setup is with more than one
                # segment pr. connection (e.g. reservoir cell), then we
                # would have to be smarter. Either averaging the
                # properties, or be segment-centric in the output.
                #
                # Petrel happily puts many ICD segments to the same connection. This
                # setup is a bug, with partially unknown effects when simulated in Eclipse
                # Should we warn the user??

                CONicd_data = pd.merge(
                    CONdata, icd_SEGdata, right_on="ICD_SEGBRNO", left_on="CONBRNO"
                )

                # Merge SEGxxxxx to icd_conf_data
                CONSEG_data = pd.merge(
                    CONicd_data, SEGdata, left_on="ICD_SEGNXT", right_on="SEGIDX"
                )

                # Add more data:
                CONSEG_data["CompletionDP"] = 0
                nonzeroPRES = (CONSEG_data.CONPRES > 0) & (CONSEG_data.SEGPRES > 0)
                CONSEG_data.loc[nonzeroPRES, "CompletionDP"] = (
                    CONSEG_data[nonzeroPRES]["CONPRES"]
                    - CONSEG_data[nonzeroPRES]["SEGPRES"]
                )

            if not icd_present:

                # Merge SEGxxxxx to CONxxxxx data if we can find data that match them
                if "CONSEGNO" in CONdata and "SEGIDX" in SEGdata:
                    CONSEG_data = pd.merge(
                        CONdata, SEGdata, left_on="CONSEGNO", right_on="SEGIDX"
                    )
                else:
                    # Give up, you will get to distinct blocks in your CSV file when we
                    CONSEG_data = pd.concat([CONdata, SEGdata], sort=True)

            # Overwrite the CONdata structure with the augmented data structure including segments and potential ICD.
            CONdata = CONSEG_data
        CONdata["DRAWDOWN"] = 0  # Set a default so that the column always exists
        if (
            "CONPRES" in CONdata.columns
        ):  # Only try to calculate this if CONPRES is actually nonzero.
            CONdata.loc[CONdata.CONPRES > 0, "DRAWDOWN"] = (
                CONdata[CONdata.CONPRES > 0]["PRESSURE"]
                - CONdata[CONdata.CONPRES > 0]["CONPRES"]
            )

        CONdata["DATE"] = str(date)
        CONdata["WELL"] = well
        CONdata["WELLMODEL"] = wellmodel

        # Replicate S3Graf calculated data:
        if "PRESSURE" in CONdata.columns:
            CONdata["CONBPRES"] = CONdata["PRESSURE"]  # Just an alias
        if "CONLENEN" in CONdata.columns and "CONLENST" in CONdata.columns:
            CONdata["CONMD"] = 0.5 * (CONdata.CONLENST + CONdata.CONLENEN)
            CONdata["CONLENTH"] = CONdata.CONLENEN - CONdata.CONLENST

        if "CONORAT" in CONdata.columns and "CONLENTH" in CONdata.columns:
            CONdata["CONORATS"] = CONdata.CONORAT / CONdata.CONLENTH
            CONdata["CONWRATS"] = CONdata.CONWRAT / CONdata.CONLENTH
            CONdata["CONGRATS"] = CONdata.CONGRAT / CONdata.CONLENTH

        rftdata = rftdata.append(CONdata, ignore_index=True)

    # Fill empty cells with zeros. This is to avoid Spotfire interpreting columns with numbers as strings. An alternative solution
    # that keeps NaN would be to add a second row in the output containing the datatype
    rftdata.fillna(0, inplace=True)

    # The HOSTGRID data seems often to be empty, check if it is and delete if so:
    if "HOSTGRID" in rftdata.columns:
        if len(rftdata.HOSTGRID.unique()) == 1:
            if rftdata.HOSTGRID.unique()[0].strip() == "":
                del rftdata["HOSTGRID"]

    return rftdata


# Remaining functions are for the command line interface


def parse_args():
    """Parse sys.argv using argparse"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "DATAFILE",
        help="Name of Eclipse DATA file. " + "UNSMRY file must lie alongside.",
    )
    parser.add_argument(
        "-o", "--output", type=str, help="name of output csv file.", default="rft.csv"
    )
    return parser.parse_args()


def main():
    """Entry-point for module, for command line utility"""
    args = parse_args()
    eclfiles = EclFiles(args.DATAFILE)
    rft_df = rft2df(eclfiles)
    rft_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)


# Interesting documentation from S3GRAF
## Vector	Description
## CONDEPTH	Depth at the centre of each connection in the well
## CONLENST	Length down the tubing from the BH reference point to the start of the connection
## CONLENEN	Length down the tubing from the BH reference point to the far end of the connection
## CONPRES	Pressure in the wellbore at the connection
## CONORAT	Oil production rate of the connection at surface conditions
## CONWRAT	Water production rate of the connection at surface conditions
## CONGRAT	Gas production rate of the connection at surface conditions
## CONOTUB	Oil flow rate through the tubing at the start of the connection at surface conditions
## CONWTUB	Water flow rate through the tubing at the start of the connection at surface conditions
## CONGTUB	Gas flow rate through the tubing at the start of the connection at surface conditions
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
## CONBPRES	Pressure of the grid block of the connection (Copy of the PRESSURE data)
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
## SEGLENST	Length down the tubing from the zero tubing length reference point to the start of the segment
## SEGLELEN	Length down the tubing from the zero tubing length reference point to the far end of the segment
## SEGXCORD	X-coordinate at the far end of the segment (as entered by the 11th item of the WELSEGS record)
## SEGXCORD	Y-coordinate at the far end of the segment (as entered by the 12th item of the WELSEGS record)
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
