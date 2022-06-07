"""Parser and dataframe generator for the Eclipse keywords:
  * COMPDAT
  * COMPLUMP
  * COMPSEGS
  * WELOPEN
  * WELSEGS
  * WLIST
  * WSEGAICD
  * WSEGSICD
  * WSEGVALV
"""

import argparse
import datetime
import logging
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

try:
    # pylint: disable=unused-import
    import opm.io.deck
except ImportError:
    # Allow parts of ecl2df to work without OPM:
    pass

from ecl2df import getLogger_ecl2csv

from .common import (
    get_wells_matching_template,
    merge_zones,
    parse_opmio_date_rec,
    parse_opmio_deckrecord,
    parse_opmio_tstep_rec,
    write_dframe_stdout_file,
)
from .eclfiles import EclFiles
from .grid import merge_initvectors

logger = logging.getLogger(__name__)

"""OPM authors and Roxar RMS authors have interpreted the Eclipse
documentation ever so slightly different when naming the data.

For COMPDAT dataframe columnnames, we prefer the RMS terms due to the
one very long one, and mixed-case in opm
"""
COMPDAT_RENAMER: Dict[str, str] = {
    "WELL": "WELL",
    "I": "I",
    "J": "J",
    "K1": "K1",
    "K2": "K2",
    "STATE": "OP/SH",
    "SAT_TABLE": "SATN",
    "CONNECTION_TRANSMISSIBILITY_FACTOR": "TRAN",
    "DIAMETER": "WBDIA",
    "Kh": "KH",
    "SKIN": "SKIN",
    "D_FACTOR": "DFACT",
    "DIR": "DIR",
    "PR": "PEQVR",
}

# Workaround an inconsistency in JSON-files for OPM-common < 2021.04:
WSEG_RENAMER: Dict[str, str] = {
    "SEG1": "SEGMENT1",
    "SEG2": "SEGMENT2",
}


def deck2dfs(
    deck: "opm.io.Deck",
    start_date: Optional[Union[str, datetime.date]] = None,
    unroll: bool = True,
) -> Dict[str, pd.DataFrame]:
    """Loop through the deck and pick up information found

    The loop over the deck is a state machine, as it has to pick up dates and
    potential information from the WELSPECS keyword.

    Args:
        deck: A deck representing the schedule
            Does not have to be a full Eclipse deck, an include file is sufficient
        start_date: The default date to use for
            events where the DATE or START keyword is not found in advance.
            Default: None
        unroll: Whether to unroll rows that cover a range,
            like K1 and K2 in COMPDAT and in WELSEGS. Defaults to True.

    Returns:
        Dictionary with dataframes, at least for COMPDAT, COMPSEGS and WELSEGS.
    """
    compdatrecords = []  # List of dicts of every line in input file
    compsegsrecords = []
    welopenrecords = []
    welsegsrecords = []
    wsegsicdrecords = []
    wsegaicdrecords = []
    wsegvalvrecords = []
    wlistrecords = []
    complumprecords = []
    welspecs = {}
    date = start_date  # DATE column will always be there, but can contain NaN/None
    for idx, kword in enumerate(deck):
        if kword.name in ["DATES", "START"]:
            for rec in kword:
                date = parse_opmio_date_rec(rec)
                logger.info("Parsing at date %s", str(date))
        elif kword.name == "TSTEP":
            if not date:
                logger.critical("Can't use TSTEP when there is no start_date")
                return {}
            for rec in kword:
                steplist = parse_opmio_tstep_rec(rec)
                # Assuming not LAB units, then the unit is days.
                days = sum(steplist)
                assert isinstance(date, datetime.date)
                date += datetime.timedelta(days=days)
                logger.info(
                    "Advancing %s days to %s through TSTEP", str(days), str(date)
                )
        elif kword.name == "WELSPECS":
            # Information from WELSPECS are to be used in case
            # 0 or 1* is used in the I or J column in COMPDAT
            # Only the latest information pr. well is stored.
            for wellrec in kword:
                welspecs_rec_dict = parse_opmio_deckrecord(wellrec, "WELSPECS")
                welspecs[welspecs_rec_dict["WELL"]] = {
                    "I": welspecs_rec_dict["HEAD_I"],
                    "J": welspecs_rec_dict["HEAD_J"],
                }
        elif kword.name == "COMPDAT":
            for rec in kword:  # Loop over the lines inside COMPDAT record
                rec_data = parse_opmio_deckrecord(
                    rec, "COMPDAT", renamer=COMPDAT_RENAMER
                )
                rec_data["DATE"] = date
                rec_data["KEYWORD_IDX"] = idx
                if rec_data["I"] == 0:
                    if rec_data["WELL"] not in welspecs:
                        raise ValueError(
                            "WELSPECS must be provided when I is defaulted in COMPDAT"
                        )
                    rec_data["I"] = welspecs[rec_data["WELL"]]["I"]
                if rec_data["J"] == 0:
                    if rec_data["WELL"] not in welspecs:
                        raise ValueError(
                            "WELSPECS must be provided when J is defaulted in COMPDAT"
                        )
                    rec_data["J"] = welspecs[rec_data["WELL"]]["J"]
                compdatrecords.append(rec_data)
        elif kword.name == "WSEGSICD":
            for rec in kword:  # Loop over the lines inside WSEGSICD record
                rec_data = parse_opmio_deckrecord(rec, "WSEGSICD", renamer=WSEG_RENAMER)
                rec_data["DATE"] = date
                rec_data["KEYWORD_IDX"] = idx
                wsegsicdrecords.append(rec_data)
        elif kword.name == "WSEGAICD":
            for rec in kword:  # Loop over the lines inside WSEGAICD record
                rec_data = parse_opmio_deckrecord(rec, "WSEGAICD", renamer=WSEG_RENAMER)
                rec_data["DATE"] = date
                rec_data["KEYWORD_IDX"] = idx
                wsegaicdrecords.append(rec_data)
        elif kword.name == "WSEGVALV":
            for rec in kword:  # Loop over the lines inside WSEGVALV record
                rec_data = parse_opmio_deckrecord(rec, "WSEGVALV")
                rec_data["DATE"] = date
                rec_data["KEYWORD_IDX"] = idx
                wsegvalvrecords.append(rec_data)
        elif kword.name == "COMPSEGS":
            wellname = parse_opmio_deckrecord(
                kword[0], "COMPSEGS", itemlistname="records", recordindex=0
            )["WELL"]
            for recidx in range(1, len(kword)):
                rec = kword[recidx]
                rec_data = parse_opmio_deckrecord(
                    rec, "COMPSEGS", itemlistname="records", recordindex=1
                )
                rec_data["WELL"] = wellname
                rec_data["DATE"] = date
                compsegsrecords.append(rec_data)
        elif kword.name == "WELOPEN":
            for rec in kword:
                rec_data = parse_opmio_deckrecord(rec, "WELOPEN")
                rec_data["DATE"] = date
                rec_data["KEYWORD_IDX"] = idx
                if rec_data["STATUS"] not in ["OPEN", "SHUT", "STOP", "AUTO", "POPN"]:
                    logger.warning(
                        (
                            "WELOPEN status %s is not a valid "
                            "COMPDAT state. Using 'SHUT' instead."
                        ),
                        rec_data["STATUS"],
                    )
                    rec_data["STATUS"] = "SHUT"
                welopenrecords.append(rec_data)
        elif kword.name == "WELSEGS":
            # First record contains meta-information for well
            # (opm deck returns default values for unspecified items.)
            welsegsdict = parse_opmio_deckrecord(
                kword[0], "WELSEGS", itemlistname="records", recordindex=0
            )
            # Loop over all subsequent records.
            for recidx in range(1, len(kword)):
                rec = kword[recidx]
                # WARNING: We assume that SEGMENT1 === SEGMENT2 (!!!) (if not,
                # we need to loop over a range just as for layer in compdat)
                rec_data = welsegsdict.copy()
                rec_data["DATE"] = date
                rec_data.update(
                    parse_opmio_deckrecord(
                        rec, "WELSEGS", itemlistname="records", recordindex=1
                    )
                )
                if "INFO_TYPE" in rec_data and rec_data["INFO_TYPE"] == "ABS":
                    rec_data["SEGMENT_MD"] = rec_data["SEGMENT_LENGTH"]
                welsegsrecords.append(rec_data)
        elif kword.name == "WLIST":
            for rec in kword:
                rec_data = parse_opmio_deckrecord(rec, "WLIST")
                rec_data["DATE"] = date
                if isinstance(rec_data["WELLS"], list):
                    rec_data["WELLS"] = " ".join(rec_data["WELLS"])

                # Do not store the asterisk that is needed in the Eclipse
                # keywords for referring to well lists:
                rec_data["NAME"] = rec_data["NAME"].replace("*", "")

                wlistrecords.append(rec_data)
        elif kword.name == "COMPLUMP":
            for rec in kword:  # Loop over the lines inside COMPLUMP record
                rec_data = parse_opmio_deckrecord(rec, "COMPLUMP")
                rec_data["DATE"] = date
                complumprecords.append(rec_data)

    compdat_df = pd.DataFrame(compdatrecords)
    welopen_df = pd.DataFrame(welopenrecords)
    wlist_df = pd.DataFrame(wlistrecords)
    complump_df = pd.DataFrame(complumprecords)

    if unroll and not compdat_df.empty:
        compdat_df = unrolldf(compdat_df, "K1", "K2")

    if not welopen_df.empty:
        compdat_df = applywelopen(
            compdat_df,
            expand_welopen(welopen_df, compdat_df),
            expand_wlist(wlist_df),
            unroll_complump(complump_df),
        )

    compsegs_df = pd.DataFrame(compsegsrecords)
    welsegs_df = pd.DataFrame(welsegsrecords)
    wsegsicd_df = pd.DataFrame(wsegsicdrecords)
    wsegaicd_df = pd.DataFrame(wsegaicdrecords)
    wsegvalv_df = pd.DataFrame(wsegvalvrecords)

    if unroll and not welsegs_df.empty:
        welsegs_df = unrolldf(welsegs_df, "SEGMENT1", "SEGMENT2")

    if unroll and not wsegsicd_df.empty:
        wsegsicd_df = unrolldf(wsegsicd_df, "SEGMENT1", "SEGMENT2")

    if unroll and not wsegaicd_df.empty:
        wsegaicd_df = unrolldf(wsegaicd_df, "SEGMENT1", "SEGMENT2")

    if "KEYWORD_IDX" in compdat_df.columns:
        compdat_df.drop(["KEYWORD_IDX"], axis=1, inplace=True)

    if "KEYWORD_IDX" in wsegsicd_df.columns:
        wsegsicd_df.drop(["KEYWORD_IDX"], axis=1, inplace=True)

    if "KEYWORD_IDX" in wsegaicd_df.columns:
        wsegaicd_df.drop(["KEYWORD_IDX"], axis=1, inplace=True)

    if "KEYWORD_IDX" in wsegvalv_df.columns:
        wsegvalv_df.drop(["KEYWORD_IDX"], axis=1, inplace=True)

    return dict(
        COMPDAT=compdat_df,
        COMPSEGS=compsegs_df,
        WELSEGS=welsegs_df,
        WELOPEN=welopen_df,
        WLIST=wlist_df,
        WSEGSICD=wsegsicd_df,
        WSEGAICD=wsegaicd_df,
        WSEGVALV=wsegvalv_df,
    )


def expand_welopen(welopen_df: pd.DataFrame, compdat_df: pd.DataFrame) -> pd.DataFrame:
    """Expands WELOPEN. First wildcard wells are expanded and then default
    coordinates are expanded. The order of the expansion is important.
    """
    exp_welopen_df = expand_welopen_wildcards(welopen_df, compdat_df)
    return expand_welopen_defaults(exp_welopen_df, compdat_df)


def expand_welopen_defaults(
    welopen_df: pd.DataFrame, compdat_df: pd.DataFrame
) -> pd.DataFrame:
    """Expands rows in WELOPEN where one or two coordinates are defaulted.
    Expansion happens by filtering on compdat rows that are matching the
    well name and the coordinates that are not defaulted.

    If all coordinates (I, J, K) are defaulted then the WELOPEN keyword
    is acting on the well and not on the connections, and shall not be
    expanded.

    It is important that expansion of wildcard wells is done prior to
    this function and that COMPDAT is unrolled so that K1=K2 in the input
    to this functions.
    """

    def is_default(value: Optional[int]) -> bool:
        if value is None or np.isnan(value):
            return True
        return value <= 0

    exp_welopen = []
    for _, row in welopen_df.iterrows():
        coord_defaulted = [is_default(row[coord]) for coord in ["I", "J", "K"]]
        if all(coord_defaulted) or not any(coord_defaulted):
            # If all coordinates are defaulted, the WELOPEN keyword is acting on
            # the well and not the connections, and shall not be expanded.
            # If no coordinates are defaulted, there is nothing to expand.
            exp_welopen.append(row)
        else:
            # If some of the coordinates are defaulted then we filter the
            # compdat dataframe to find the matching connections and expand
            # the WELOPEN row with those

            # Any compdat entry with DATE==None are kept as they
            # are assumed to have an earlier date than any dates defined
            compdat_filtered = compdat_df[compdat_df["DATE"].isnull()]

            # If the welopen entry DATE!=None we filter on compdat entries
            # <= this date
            if row["DATE"] is not None:
                compdat_filtered = pd.concat(
                    [compdat_filtered, compdat_df[compdat_df["DATE"] <= row["DATE"]]]
                )

            # Filter on well name
            compdat_filtered = compdat_filtered[compdat_filtered["WELL"] == row["WELL"]]

            # Filter on coordinates
            for coord in ["I", "J", "K"]:
                # In COMPDAT the K coordinate is named K1/K2.
                compdat_coord = coord + "1" if coord == "K" else coord
                if not is_default(row[coord]):
                    compdat_filtered = compdat_filtered[
                        compdat_filtered[compdat_coord] == row[coord]
                    ]

            # If compdat_filtered is empty it means that no connections are matching
            # the criterias in the WELOPEN row.
            if compdat_filtered.empty:
                raise ValueError(
                    "No connections are matching WELOPEN keyword with defaulted "
                    "coordinates:"
                    f"\n {row} "
                )

            for _, compdat_row in compdat_filtered.iterrows():
                exp_row = row.copy()
                exp_row["I"] = compdat_row["I"]
                exp_row["J"] = compdat_row["J"]
                exp_row["K"] = compdat_row["K1"]
                exp_welopen.append(exp_row)
    return pd.DataFrame(exp_welopen)


def expand_welopen_wildcards(
    welopen_df: pd.DataFrame, compdat_df: pd.DataFrame
) -> pd.DataFrame:
    """Expand rows in welopen with well names containing wildcard characters,
    with the correct wells from compdat_df that was defined at that date

    Example::

      WELOPEN
       'OP*' 'SHUT' /
      /

    might become the equivalent dataframe representation of::

      WELOPEN
       'OP1' 'SHUT' /
       'OP2' 'SHUT' /
      /

    if both OP1 and OP2 are defined at that time.

    Args:
        welopen_df: DataFrame with welopen
        compdat_df: DataFrame with compdat

    Returns:
        Expanded welopen dataframe
    """
    exp_welopen = []
    for _, row in welopen_df.iterrows():
        if row["WELL"].startswith("*"):
            # This means that the WELL field is refering to a well list
            # This is handled elsewhere and we let it pass here
            exp_welopen.append(row)
        elif "*" in row["WELL"] or "?" in row["WELL"]:
            # This row is identified a well name template with wildcard characters
            relevant_wells = compdat_df[compdat_df["DATE"] <= row["DATE"]][
                "WELL"
            ].unique()
            matched_wells = get_wells_matching_template(row["WELL"], relevant_wells)
            for well in matched_wells:
                exp_row = row.copy()
                exp_row["WELL"] = well
                exp_welopen.append(exp_row)
        else:
            exp_welopen.append(row)
    return pd.DataFrame(exp_welopen)


def unrolldf(
    dframe: pd.DataFrame, start_column: str = "K1", end_column: str = "K2"
) -> pd.DataFrame:
    """Unroll dataframes, where some column pairs indicate
    a range where data applies.

    After unrolling, column pairs with ranges are transformed
    into multiple rows, with no ranges.

    Example: COMPDAT supports K1, K2 intervals for multiple cells::

      COMPDAT
        'OP1' 33 44 10 11 /
      /

    is transformed/unrolled so it would be equal to::

      COMPDAT
        'OP1' 33 44 10 10 /
        'OP1' 33 44 11 11 /
      /

    The latter is easier to work with in Pandas dataframes

    Args:
        dframe: Dataframe to be unrolled
        start_column: Column name that contains the start of
            a range.
        end_column Column name that contains the corresponding end
            of the range.

    Returns:
        Dataframe, unrolled version. Identical to input if none of
        rows had any ranges.
    """
    if dframe.empty:
        return dframe
    if start_column not in dframe and end_column not in dframe:
        logger.warning(
            "Cannot unroll on non-existing columns %s and %s", start_column, end_column
        )
        return dframe
    start_eq_end_bools = dframe[start_column] == dframe[end_column]
    unrolled = dframe[start_eq_end_bools]
    list_unrolled = []
    if (~start_eq_end_bools).any():
        for _, rangerow in dframe[~start_eq_end_bools].iterrows():
            for k_idx in range(
                int(rangerow[start_column]), int(rangerow[end_column]) + 1
            ):
                rangerow[start_column] = k_idx
                rangerow[end_column] = k_idx
                list_unrolled.append(rangerow.copy())
    if list_unrolled:
        unrolled = pd.concat([unrolled, pd.DataFrame(list_unrolled)], axis=0)
    return unrolled


def unroll_complump(complump_df: pd.DataFrame) -> pd.DataFrame:
    """Unrolls the COMPLUMP keyword where K2>K1. Uses the unrolldf function,
    but this function gives more precise handling of errors.

    Example::

      COMPLUMP
       'OP1' 74 135 7 8 1 /
      /

    is transformed/unrolled to the dataframe representation of::

      COMPLUMP
       'OP1' 74 135 7 7 1 /
       'OP1' 74 135 8 8 1 /
      /

    Args:
        dframe: Dataframe to be unrolled

    Returns:
        Dataframe, unrolled version.
    """
    if complump_df is None or complump_df.empty:
        return complump_df

    for _, row in complump_df.iterrows():
        val_i = int(row["I"])
        val_j = int(row["J"])
        val_k1 = int(row["K1"])
        val_k2 = int(row["K2"])
        if val_i < 0 or val_j < 0 or val_k1 < 0 or val_k2 < 0:
            raise ValueError(
                f"Negative values for COMPLUMP coordinates are not allowed: {row}"
            )
        if val_i == 0 or val_j == 0 or val_k1 == 0 or val_k2 == 0:
            raise ValueError(
                f"Defaulted COMPLUMP coordinates are not supported in ecl2df: {row}"
            )
        if val_k2 < val_k1:
            raise ValueError(f"K2 must be equal to or greater than K1: {row}")
    return unrolldf(complump_df)


def expand_wlist(wlist_df: pd.DataFrame) -> pd.DataFrame:
    """Expand all WLIST actions in a dataframe into a dataframe with
    only "NEW" actions. This makes the dataframe cheaper to parse to
    get the state of the well lists at a particular date

    Example:

    .. code-block::

      WLIST
        '*OP' NEW OP1 /
        '*OP' ADD OP2 /
      /

    is transformed into the equivalent dataframe representation of:

    .. code-block::

      WLIST
        '*OP' NEW OP1 OP2 /  -- wells always sorted alphabetically
      /

    and then similarly for more complex MOV, DEL and NEW actions.

    The rationale is that if you extract all WLIST rows at a date
    and there are only NEW actions present, you can trust that dataframe
    to contain all WLIST actions accumulated from the start.

    Warning: If multiple WLIST keywords are at the same date, with other
    keywords depending on the WLIST state in between, that effect is lost
    through this dataframe representation.

    Args:
        wlist_df (pd.DataFrame): Dataframe with WLIST action rows. DATE
            must be present as a column in the DataFrame

    Returns:
        pd.DataFrame. WLIST rows with only NEW directives
    """

    # This function maintain all current (as in pr. date) well lists as a list
    # of dictionaries, which accumulates all WLIST directives. Every time the date
    # changes, the current state is outputted as it was valid for the previous date.

    currentstate: Dict[str, str] = {}

    if wlist_df.empty:
        return wlist_df

    currentdate = wlist_df["DATE"].min()
    new_records = []

    for _, wlist_record in wlist_df.iterrows():
        date = wlist_record["DATE"]
        if date > currentdate:
            # Store current state
            for wlistname, wells in currentstate.items():
                new_records.append(
                    {
                        "DATE": currentdate,
                        "NAME": wlistname,
                        "ACTION": "NEW",
                        "WELLS": wells,
                    }
                )
        currentdate = date

        if wlist_record["ACTION"] in ["ADD", "NEW"]:
            # Already defined well-lists can be used to append whole
            # well lists to other lists:
            recursive_wlists = [
                r_wlist
                for r_wlist in wlist_record["WELLS"].split()
                if r_wlist.startswith("*")
            ]
            for r_wlist in recursive_wlists:
                if r_wlist[1:] in currentstate:
                    wlist_record["WELLS"] = wlist_record["WELLS"].replace(
                        r_wlist, currentstate[r_wlist[1:]]
                    )
                else:
                    print(wlist_record)
                    raise ValueError(
                        f"Recursive well list {r_wlist} does not exist in "
                        f"{currentstate}"
                    )
        if wlist_record["ACTION"] == "NEW":
            currentstate[wlist_record["NAME"]] = " ".join(
                sorted(wlist_record["WELLS"].split())
            )
        elif wlist_record["ACTION"] in ["ADD", "DEL"]:
            if wlist_record["NAME"] not in currentstate:
                raise ValueError(
                    "WLIST ADD/DEL only works on existing well lists: "
                    f"{str(wlist_record)}"
                )
        if wlist_record["ACTION"] == "ADD":
            currentstate[wlist_record["NAME"]] = " ".join(
                sorted(
                    set(
                        wlist_record["WELLS"].split()
                        + currentstate[wlist_record["NAME"]].split()
                    )
                )
            )
        if wlist_record["ACTION"] == "DEL":
            currentstate[wlist_record["NAME"]] = " ".join(
                sorted(
                    list(
                        set(currentstate[wlist_record["NAME"]].split())
                        - set(wlist_record["WELLS"].split())
                    )
                )
            )
        if wlist_record["ACTION"] == "MOV":
            if wlist_record["NAME"] not in currentstate:
                currentstate[wlist_record["NAME"]] = ""
            currentstate[wlist_record["NAME"]] = " ".join(
                sorted(
                    list(
                        set(currentstate[wlist_record["NAME"]].split()).union(
                            set(wlist_record["WELLS"].split())
                        )
                    )
                )
            )
            for (
                wlist
            ) in currentstate.keys():  # pylint: disable=consider-iterating-dictionary
                if wlist == wlist_record["NAME"]:
                    continue
                currentstate[wlist] = " ".join(
                    sorted(
                        list(
                            set(currentstate[wlist].split())
                            - set(wlist_record["WELLS"].split())
                        )
                    )
                )

    # Dump final state:
    for wlistname, wells in currentstate.items():
        new_records.append(
            {"DATE": currentdate, "NAME": wlistname, "ACTION": "NEW", "WELLS": wells}
        )

    return pd.DataFrame(new_records)


def expand_complump_in_welopen_df(
    welopen_df: pd.DataFrame, complump_df: pd.DataFrame
) -> pd.DataFrame:
    """Go through all elements of WELOPEN and expand the rows
    referring to COMPLUMPS. The output dataframe is as if the
    connections were refered to explicitly in WELOPEN:

    Example: COMPLUMP and WELOPEN keywords::

      COMPLUMP
       'OP1' 74 135 7 7 1 /
       'OP1' 74 136 8 8 1 /
       'OP1' 74 136 9 9 2 /
       'OP1' 74 137 10 10 3 /
      /
      WELOPEN
       'OP1' 'SHUT' 3* 1 1 /
      /

    is transformed into the equivalent dataframe representation of::

      WELOPEN
       'OP1' 'SHUT' 74 135 7 /
       'OP1' 'SHUT' 74 135 8 /
      /

    Args:
        welopen_df: Dataframe with WELOPEN actions
        complump_df: Dataframe with COMPLUMP records. Optional.

    Returns:
        welopen_df with complump expanded to actual connections.

    """

    if (
        welopen_df is None
        or welopen_df.empty
        or complump_df is None
        or complump_df.empty
    ):
        return welopen_df

    exp_welopens = []
    for _, row in welopen_df.iterrows():
        if row["C1"] is None and row["C2"] is None:
            exp_welopens.append(row)
        elif row["C1"] is None or row["C2"] is None:
            raise ValueError(
                "Both or none of the completions numbers in "
                f"WELOPEN must be defined: {row}"
            )
        else:
            # Found a row that refers to complump numbers
            # Check that the cumplump numbers are ok:
            c_1, c_2 = int(row["C1"]), int(row["C2"])
            if c_1 < 0 or c_2 < 0:
                raise ValueError(f"Negative values for C1/C2 is not allowed: {row}")
            if c_1 == 0 or c_2 == 0:
                raise ValueError(f"Zeros for C1/C2 is not implemented: {row}")
            if c_2 < c_1:
                raise ValueError(f"C2 must be equal or greater than C1: {row}")

            relevant_complump_df = complump_df[
                (complump_df["DATE"] <= row["DATE"])
                & (complump_df["WELL"] == row["WELL"])
                & (complump_df["N"] >= c_1)
                & (complump_df["N"] <= c_2)
            ]
            # If I, J and K is also present in the WELOPEN record
            # we should "and" the complump filter and the i,j,k filter:
            if (
                {"I", "J", "K"}.issubset(row.keys())
                and row["I"]
                and row["J"]
                and row["K"]
            ):
                relevant_complump_df = relevant_complump_df[
                    (relevant_complump_df["I"] == row["I"])
                    & (relevant_complump_df["J"] == row["J"])
                    & (relevant_complump_df["K1"] == row["K"])
                    & (relevant_complump_df["K2"] == row["K"])
                ]
            for _, complump_row in relevant_complump_df.iterrows():
                if complump_row["K1"] != complump_row["K2"]:
                    raise ValueError(
                        "K1 must be equal to K2 in COMPLUMP "
                        f"(K2>K1 must be expanded elsewhere): {complump_row}"
                    )
                cell_row = row.copy()
                cell_row["I"] = complump_row["I"]
                cell_row["J"] = complump_row["J"]
                cell_row["K"] = complump_row["K1"]
                cell_row["C1"] = None
                cell_row["C2"] = None
                exp_welopens.append(cell_row)

    dframe = pd.DataFrame(exp_welopens)
    return dframe.astype(object).where(pd.notnull(dframe), None)


def expand_wlist_in_welopen_df(
    welopen_df: pd.DataFrame, wlist_df: pd.DataFrame
) -> pd.DataFrame:
    """Go trough a welopen dataframe and expand rows where the well-name refers
    to a well-list. The returned dataframe is as if the welopen commands were
    inputted explicitly without the use of WLIST.
    """
    if welopen_df.empty or welopen_df is None or wlist_df is None or wlist_df.empty:
        return welopen_df

    exp_welopens = []
    for _, row in welopen_df.iterrows():
        relevant_wlist_df = wlist_df[wlist_df["DATE"] <= row["DATE"]]
        if row["WELL"].startswith("*"):
            wlistname = row["WELL"].replace("*", "")
            if wlistname in relevant_wlist_df["NAME"].to_numpy():
                for well in (
                    relevant_wlist_df[relevant_wlist_df["NAME"] == wlistname]
                    .tail(1)["WELLS"]
                    .reset_index(drop=True)[0]
                    .split()
                ):
                    wellrow = row.copy()
                    wellrow.update({"WELL": well})
                    exp_welopens.append(wellrow)
            else:
                raise ValueError(f"Well list {wlistname} not defined at {row['DATE']}")
        else:
            # Explicit wellname was used, no expansion to happen:
            exp_welopens.append(row)
    dframe = pd.DataFrame(exp_welopens)
    return dframe.astype(object).where(pd.notnull(dframe), None)


def applywelopen(
    compdat_df: pd.DataFrame,
    welopen_df: pd.DataFrame,
    wlist_df: Optional[pd.DataFrame] = None,
    complump_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Apply WELOPEN actions to the COMPDAT dataframe.

    Each record in the WELOPEN keyword acts as an operator on existing connections
    in existing wells.

    Example: COMPDAT and WELOPEN keyword::

      COMPDAT
       'OP1' 33 44 10 11 'OPEN' /
       'OP2' 66 44 10 11 'OPEN' /
      /
      WELOPEN
       'OP1' SHUT /
       'OP2' SHUT 66 44 10 /
      /

    This deck would define two wells where OP1 and OP2 have two connected grid cells
    each. The first welopen statment acts on the whole well, closing both the well and
    the connections. If this statement used STOP instead of SHUT, the connections would
    be left open. The second welopen statement acts on a single connection. Here SHUT
    and STOP would give the same result. This behavior has been proven to be correct
    in the simulator. The Eclipse manual states that 'If items 3 - 7 are all defaulted,
    the Open/Shut/Stop command applies to the well, leaving the connections unchanged',
    but this has been proven to be wrong. The state of the connection can be tested
    by looking at the CPI summary vectors. The connection is SHUT if CPI==0 and OPEN
    if CPI>0.

    WELOPEN can also be used at different dates and changes therefore the state of
    connections without explicit use of the COMPDAT keyword. This function translates
    WELOPEN actions into explicit additional COMPDAT definitions in the exported df.

    Args:
        compdat_df: Dataframe with unrolled COMPDAT data
        welopen_df: Dataframe with WELOPEN actions
        wlist_df: Dataframe with WLIST NEW records. Optional.
        complump_df: Dataframe with COMPLUMP records. Optional.

    Returns:
        compdat_df now including WELOPEN actions

    """
    if isinstance(wlist_df, pd.DataFrame):
        if wlist_df.empty:
            wlist_df = None
        else:
            if set(wlist_df["ACTION"]) != {"NEW"}:
                raise ValueError(
                    "The WLIST dataframe must be expanded through expand_wlist()"
                )

    welopen_df = welopen_df.astype(object).where(pd.notnull(welopen_df), None)
    welopen_df = expand_wlist_in_welopen_df(welopen_df, wlist_df)
    welopen_df = expand_complump_in_welopen_df(welopen_df, complump_df)

    for _, row in welopen_df.iterrows():
        acts_on_well = False
        if (row["I"] is None and row["J"] is None and row["K"] is None) or (
            row["I"] <= 0 and row["J"] <= 0 and row["K"] <= 0
        ):
            # Applies to all connections when the completion range
            # is set zero or negative.
            previous_state = compdat_df[
                (compdat_df["WELL"] == row["WELL"])
                & (compdat_df["KEYWORD_IDX"] < row["KEYWORD_IDX"])
            ].drop_duplicates(subset=["I", "J", "K1", "K2"], keep="last")
            acts_on_well = True
        elif (
            row["I"]
            and row["J"]
            and row["K"]
            and row["C1"] is None
            and row["C2"] is None
        ):
            # The compdat dataframe is assumed unrolled
            # so that K1 is always equal to K2. Any openings of lumped
            # connections (C1 and C2) should already be translated to
            # I, J, and K when we get here.
            previous_state = compdat_df[
                (compdat_df["WELL"] == row["WELL"])
                & (compdat_df["KEYWORD_IDX"] < row["KEYWORD_IDX"])
                & (compdat_df["I"] == row["I"])
                & (compdat_df["J"] == row["J"])
                & (compdat_df["K1"] == row["K"])
                & (compdat_df["K2"] == row["K"])
            ].drop_duplicates(subset=["I", "J", "K1", "K2"], keep="last")
        else:
            raise ValueError(
                "A WELOPEN keyword contains data that could not be parsed. "
                f"\n {row} "
            )

        if previous_state.empty:
            raise ValueError(
                "A WELOPEN keyword is not acting on any existing connection. "
                f"\n {row} "
            )

        new_state = previous_state

        # The COMPDAT DataFrame uses COMPDAT_RENAMER and therefore uses "OP/SH" as a
        # column name for the state of a well. WELOPEN uses "STATUS" for the state
        # column name and therefore a translation step needs to be done. The
        # underlying problem is that the opm-common definitions for the state of a
        # well in COMPDAT and WELOPEN are not identical. These translation steps can
        # be dropped when unity in the opm-common keyword definitions is reached.
        new_state["OP/SH"] = row["STATUS"].replace("POPN", "OPEN")

        # If the welopen statement acts on the whole well, then STOP closes the well
        # but opens the connections. If the welopen statement applies to selected
        # connections, then STOP means the same as SHUT.
        if acts_on_well:
            new_state["OP/SH"] = new_state["OP/SH"].replace("STOP", "OPEN")
        else:
            new_state["OP/SH"] = new_state["OP/SH"].replace("STOP", "SHUT")

        new_state["KEYWORD_IDX"] = row["KEYWORD_IDX"]
        new_state["DATE"] = row["DATE"]

        compdat_df = compdat_df.append(new_state)

    if not compdat_df.empty:
        compdat_df = (
            compdat_df.sort_values(by=["KEYWORD_IDX"])
            .drop_duplicates(subset=["WELL", "I", "J", "K1", "K2", "DATE"], keep="last")
            .reset_index(drop=True)
        )

    return compdat_df


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser: parser to fill with arguments
    """
    parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file.",
        default="compdat.csv",
    )
    parser.add_argument(
        "--initvectors",
        help="List of INIT vectors to merge into the data",
        nargs="+",
        default=None,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def compdat_main(args):
    """Entry-point for module, for command line utility"""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    eclfiles = EclFiles(args.DATAFILE)
    compdat_df = df(eclfiles, initvectors=args.initvectors)
    write_dframe_stdout_file(compdat_df, args.output, index=False, caller_logger=logger)


def df(
    eclfiles: EclFiles,
    initvectors: Optional[List[str]] = None,
    zonemap: Optional[Dict[int, str]] = None,
) -> pd.DataFrame:
    """Main function for Python API users

    Supports only COMPDAT information for now. Will
    add a zone-name if a zonefile is found alongside.
    If a zonemap is passed it will override the zonefile.

    Returns:
        pd.Dataframe with one row pr cell to well connection
    """
    compdat_df = deck2dfs(eclfiles.get_ecldeck())["COMPDAT"]
    compdat_df = unrolldf(compdat_df)

    if initvectors:
        compdat_df = merge_initvectors(
            eclfiles, compdat_df, initvectors, ijknames=["I", "J", "K1"]
        )

    if zonemap is None:
        # If no zonemap is submitted, search for zonemap in default location
        zonemap = eclfiles.get_zonemap()

    if zonemap:
        logger.info("Merging zonemap into compdat")
        compdat_df = merge_zones(compdat_df, zonemap)

    return compdat_df
