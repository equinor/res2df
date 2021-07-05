"""Extract GRUPTREE information from an Eclipse deck"""

import sys
import logging
import datetime
import collections
import argparse
import warnings
from typing import Optional, Union, List, Dict, Any

import treelib
import pandas as pd

try:
    # Needed for mypy

    # pylint: disable=unused-import
    import opm.io
except ImportError:
    pass

from ecl2df import EclFiles
from ecl2df.common import (
    parse_opmio_date_rec,
    parse_opmio_deckrecord,
    parse_opmio_tstep_rec,
    write_dframe_stdout_file,
)

logger = logging.getLogger(__name__)


def df(
    deck: Union[EclFiles, "opm.libopmcommon_python.Deck"],
    startdate: Optional[datetime.date] = None,
    welspecs: bool = True,
) -> pd.DataFrame:
    """Extract all group information from a deck
    and present as a Pandas Dataframe of all edges.

    Numerical properties for nodes given in GRUPNET will
    be added as extra columns.

    From WELSPECS, well names are extracted and added
    as nodes with an edge to its group.

    The gruptree is a time dependent property,
    with accumulative effects from new occurences of
    GRUPNET, WELSPECS, BRANPROP and NODEPROP.

    Whenever the GRUPTREE or BRANPROP tree changes, the
    previous tree is copied and a new complete tree is added
    to the dataframe tagged with the new date.

    startdate is only relevant when START is not in the deck.

    Args:
        deck: opm.io Deck object or EclFiles

    Returns:
        pd.DataFrame with one row pr edge. Empty dataframe if no
        information is found in deck.
    """

    date: Optional[datetime.date]
    if startdate is not None:
        date = startdate
    else:
        date = None

    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()

    edgerecords = []  # list of dict of rows containing an edge.
    nodedatarecords = []

    # In order for the GRUPTREE/BRANPROP keywords to accumulate, we
    # store the edges as a dictionary indexed by the edge
    # (which is a tuple of child and parent).
    # The value of the dictionary is GRUPTREE or WELSPECS
    currentedges: Dict[str, Dict[tuple, Dict[str, Any]]] = {
        "GRUPTREE": dict(),
        "BRANPROP": dict(),
    }
    wellspecsedges: Dict[tuple, str] = dict()
    nodedata: Dict[str, pd.DataFrame] = {
        "GRUPNET": pd.DataFrame(),
        "NODEPROP": pd.DataFrame(),
    }

    # Flags which will tell when a new GRUPTREE/BRANPROP, WELSPECS or
    # GRUPNET/NODEPROP have been encountered
    keywords = ["GRUPTREE", "BRANPROP", "WELSPECS", "GRUPNET", "NODEPROP"]
    found_keywords = {key: False for key in keywords}
    for kword in deck:
        if kword.name == "DATES" or kword.name == "START" or kword.name == "TSTEP":
            # Whenever we encounter a new DATES, it means that
            # we have processed all the GRUPTREE and WELSPECS that
            # have occured since the last date, so this is the chance
            # to dump the parsed data. Also we dump the *entire* tree
            # at every date with a change, not only the newfound edges.
            if any(val for val in found_keywords.values()):
                if date is None:
                    logger.warning("No date parsed, maybe you should pass --startdate")
                    logger.warning("Using 1900-01-01")
                    date = datetime.date(year=1900, month=1, day=1)
                edgerecords += _write_edgerecords(
                    currentedges, nodedata, wellspecsedges, found_keywords, date
                )
                found_keywords = {key: False for key in keywords}
            # Done dumping the data for the previous date, parse the fresh
            # date:
            if kword.name == "DATES" or kword.name == "START":
                for rec in kword:
                    date = parse_opmio_date_rec(rec)
                    logging.info("Parsing at date %s", str(date))
            elif kword.name == "TSTEP":
                assert date is not None
                for rec in kword:
                    steplist = parse_opmio_tstep_rec(rec)
                    # Assuming not LAB units, then the unit is days.
                    days = sum(steplist)
                    if days <= 0:
                        logger.critical("Invalid TSTEP, summed to %s days", str(days))
                        return pd.DataFrame()
                    date += datetime.timedelta(days=days)
                    logger.info(
                        "Advancing %s days to %s through TSTEP", str(days), str(date)
                    )
            else:
                logger.critical("BUG: Should not get here")
                return pd.DataFrame()
        if kword.name in ["GRUPTREE", "BRANPROP"]:
            found_keywords[kword.name] = True
            renamer = (
                {"DOWNTREE_NODE": "CHILD_GROUP", "UPTREE_NODE": "PARENT_GROUP"}
                if kword.name == "BRANPROP"
                else None
            )
            for edgerec in kword:
                edge_dict = parse_opmio_deckrecord(edgerec, kword.name, renamer=renamer)
                child = edge_dict.pop("CHILD_GROUP")
                parent = edge_dict.pop("PARENT_GROUP")
                currentedges[kword.name][(child, parent)] = edge_dict

        if kword.name == "WELSPECS" and welspecs:
            found_keywords["WELSPECS"] = True
            for wellrec in kword:
                wspc_dict = parse_opmio_deckrecord(wellrec, "WELSPECS")
                wellspecsedges[(wspc_dict["WELL"], wspc_dict["GROUP"])] = "WELSPECS"

        if kword.name in ["GRUPNET", "NODEPROP"]:
            found_keywords[kword.name] = True
            for rec in kword:
                nodedatarecords.append(parse_opmio_deckrecord(rec, kword.name))
            nodedata[kword.name] = (
                pd.DataFrame(nodedatarecords)
                .drop_duplicates(subset="NAME", keep="last")
                .set_index("NAME")
            )

    # Ensure we also store any tree information found after the last DATE statement
    if any([val for val in found_keywords.values()]):
        edgerecords += _write_edgerecords(
            currentedges, nodedata, wellspecsedges, found_keywords, date
        )
    dframe = pd.DataFrame(edgerecords)
    if "DATE" in dframe:
        dframe["DATE"] = pd.to_datetime(dframe["DATE"])

    # Remove duplicate rows
    # This happens with WELSPECS if GRUPTREE and BRANPROP is defined
    # at the same timestep
    dframe = dframe.drop_duplicates(
        subset=["DATE", "CHILD", "KEYWORD", "PARENT"], keep="last"
    )
    print(dframe)
    return dframe


def _write_edgerecords(
    currentedges: Dict[str, Dict[tuple, Dict[str, Any]]],
    nodedata: Dict[str, pd.DataFrame],
    wellspecsedges: Dict[tuple, str],
    found_keywords: dict,
    date: Optional[datetime.date],
) -> List[dict]:
    """
    Description
    """
    edgerecords = []
    if any([found_keywords[key] for key in ["GRUPTREE", "GRUPNET", "WELSPECS"]]):
        edgerecords += _merge_edges_and_nodeinfo(
            currentedges["GRUPTREE"],
            nodedata["GRUPNET"],
            wellspecsedges,
            date,
            "GRUPTREE",
        )
    if (
        any([found_keywords[key] for key in ["BRANPROP", "NODEPROP", "WELSPECS"]])
        and currentedges["BRANPROP"]
    ):
        edgerecords += _merge_edges_and_nodeinfo(
            currentedges["BRANPROP"],
            nodedata["NODEPROP"],
            wellspecsedges,
            date,
            "BRANPROP",
        )

    return edgerecords


def _merge_edges_and_nodeinfo(
    currentedges: Dict[tuple, Dict[str, Any]],
    nodedata_df: pd.DataFrame,
    wellspecsedges: Dict[tuple, str],
    date: Optional[datetime.date],
    treetype: str,
) -> List[dict]:
    """Merge a list of edges with information from the GRUPNET dataframe.

    Edges where there is no parent (root nodes) are identified and added
    as special cases.

    Args:
        currentedges:
        nodedata_df: Containing data for each node to add.
        date: Relevant date.

    Returns:
        List of dictionaries (that can be made into a dataframe)
    """
    edgerecords = []
    childs = set()
    parents = set()
    # Write GRUPTREE/BRANPROP edges
    for (child, parent), edge_dict in currentedges.items():
        rec_dict = {"DATE": date, "CHILD": child, "PARENT": parent, "KEYWORD": treetype}
        childs |= {child}
        parents |= {parent}

        # Add fields from edge_dict
        rec_dict.update(edge_dict)

        # Add node data
        if child in nodedata_df.index:
            rec_dict.update(nodedata_df.loc[child])
        edgerecords.append(rec_dict)

    # Write WELSPECS edges
    for (child, parent), _ in wellspecsedges.items():
        if (treetype == "BRANPROP" and parent in childs) or (treetype == "GRUPTREE"):
            rec_dict = {
                "DATE": date,
                "CHILD": child,
                "PARENT": parent,
                "KEYWORD": "WELSPECS",
            }
            edgerecords.append(rec_dict)

        if treetype == "GRUPTREE":
            childs |= {child}
            parents |= {parent}

    # If the treetype is GRUPTREE, add root nodes
    if treetype == "GRUPTREE":
        roots = parents - childs
        rootrecords = []
        for root in roots:
            rec_dict = {"DATE": date, "CHILD": root, "KEYWORD": "GRUPTREE"}
            if root in nodedata_df.index:
                rec_dict.update(nodedata_df.loc[root])
            rootrecords.append(rec_dict)
        return rootrecords + edgerecords

    return edgerecords


def edge_dataframe2dict(dframe: pd.DataFrame) -> List[dict]:
    """Convert list of edges in a dataframe into a
    nested dictionary (tree).

    The dataframe cannot have multiple DATEs, filter to the date you
    want prior to calling this function.

    Example::

      [{
        'FIELD': {'OP': {'OP_1': {},
        'OP_2': {},
        'OP_3': {},
        'OP_4': {},
        'OP_5': {}},
        'WI': {'WI_1': {}, 'WI_2': {}, 'WI_3': {}}}
      }]

    Leaf nodes have empty dictionaries as their value.

    Returns:
        List of nested dictionaries, as we in general
        may have more than one root. The list sorted
        alphabetically on the top level node name.
    """
    if dframe.empty:
        return [{}]
    if "DATE" in dframe:
        if len(dframe["DATE"].unique()) > 1:
            raise ValueError("Can only handle one date at a time")
    subtrees: dict = collections.defaultdict(dict)
    edges = []  # List of tuples
    for _, row in dframe.iterrows():
        if not pd.isnull(row["PARENT"]):
            edges.append((row["CHILD"], row["PARENT"]))
    for child, parent in edges:
        subtrees[parent][child] = subtrees[child]

    children, parents = zip(*edges)
    roots = set(parents).difference(children)
    return [{root: subtrees[root]} for root in sorted(roots)]


def _add_to_tree_from_dict(
    nested_dict: dict, name: str, tree: treelib.Tree, parent: Optional[str] = None
) -> None:
    assert isinstance(nested_dict, dict)
    tree.create_node(name, name, parent=parent)
    for key, value in sorted(nested_dict.items()):
        _add_to_tree_from_dict(nested_dict=value, name=key, tree=tree, parent=name)


def tree_from_dict(nested_dict: dict) -> treelib.Tree:
    """Convert a dictionary to a treelib Tree.

    The treelib representation of the trees is used
    for pretty-printing (in ASCII) of the tree, you
    only need to do str() of the returned result
    from this function.

    See `https://treelib.readthedocs.io/`

    Args:
        nested_dict: nested dictonary representing a tree.
    """
    if not nested_dict.keys():
        # Return an empty string, because str(treelib.Tree()) will error
        return ""
    if not len(nested_dict.keys()) == 1:
        raise ValueError(
            "The dict given to tree_from_dict() must have "
            "exactly one top level key, representing a single tree."
        )
    root_name = list(nested_dict.keys())[0]
    tree = treelib.Tree()
    _add_to_tree_from_dict(nested_dict[root_name], root_name, tree)
    return tree


def dict2treelib(name: str, nested_dict: dict) -> treelib.Tree:
    """Convert a nested dictonary to a treelib Tree
    object. This function is recursive.

    The treelib representation of the trees is used
    for pretty-printing (in ASCII) of the tree, you
    only need to do str() of the returned result
    from this function.

    See `https://treelib.readthedocs.io/`

    Args:
        name: name of root node
        nested_dict: nested dictonary of the children at the root.
    """
    warnings.warn(
        "dict2treelib() is deprecated and will be removed, use tree_from_dict()",
        FutureWarning,
    )

    tree = treelib.Tree()
    tree.create_node(name, name)
    for child in nested_dict.keys():
        tree.paste(name, dict2treelib(child, nested_dict[child]))
    return tree


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser (argparse.ArgumentParser or argparse.subparser): parser
            to fill with arguments
    """
    parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file. No CSV dump if empty",
        default="",
    )
    parser.add_argument(
        "-p",
        "--prettyprint",
        #      type=bool,
        action="store_true",
        help="Pretty-print the tree structure",
    )
    parser.add_argument(
        "--startdate",
        type=str,
        help="First schedule date if not defined in input file, YYYY-MM-DD",
        default=None,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def gruptree_main(args) -> None:
    """Entry-point for module, for command line utility."""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    if not args.output and not args.prettyprint:
        print("Nothing to do. Set --output or --prettyprint")
        sys.exit(0)
    eclfiles = EclFiles(args.DATAFILE)
    dframe = df(eclfiles.get_ecldeck(), startdate=args.startdate)
    if args.prettyprint:
        if "DATE" in dframe:
            for date in dframe["DATE"].dropna().unique():
                df_date = dframe[dframe.DATE==date]
                print("Date: " + str(date.astype("M8[D]")))

                for treetype in ["GRUPTREE", "BRANPROP"]:
                    if treetype in df_date["KEYWORD"].unique():
                        df_treetype = df_date[df_date["KEYWORD"].isin([treetype, "WELSPECS"])]
                        print(f"{treetype} trees:")
                        for tree in edge_dataframe2dict(df_treetype):
                            print(tree_from_dict(tree))
                print("")
        else:
            logger.warning("No tree data to prettyprint")
    if dframe.empty:
        logger.error("Empty GRUPTREE dataframe, not written to disk!")
    elif args.output:
        write_dframe_stdout_file(dframe, args.output, index=False, caller_logger=logger)
