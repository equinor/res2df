#!/bin/bash
#
# Run this to download a fresh copy of E100 keyword metadata from opm-common

# Default output directory (if not provided as an argument)
OUTPUT_DIR=${1:-"./"}

# Ensure the output directory exists
mkdir -p "$OUTPUT_DIR"

# Remember to sync the keyword list here with the list in common.py
keywords="
BRANPROP
COMPDAT
COMPLUMP
COMPSEGS
DENSITY
EQLDIMS
EQUIL
FAULTS
GRUPNET
GRUPTREE
NODEPROP
PBVD
PDVD
PVDG
PVDO
PVTG
PVTO
PVTW
ROCK
RSVD
RVVD
SGFN
SGOF
SGWFN
SLGOF
SOF2
SOF3
SWFN
SWOF
TABDIMS
VFPPROD
VFPINJ
WCONHIST
WCONINJE
WCONINJH
WCONPROD
WELOPEN
WELSEGS
WELSPECS
WLIST
WSEGAICD
WSEGSICD
WSEGVALV
"

for keyword in $keywords; do
    firstletter=${keyword:0:1}
    wget https://raw.githubusercontent.com/OPM/opm-common/master/opm/input/eclipse/share/keywords/000_Eclipse100/$firstletter/$keyword -O "$OUTPUT_DIR/$keyword"

    # Assume that the presence of num_tables in some keywords is sort of a bug:
    perl -p -i -e 's/num_tables/size/g' "$OUTPUT_DIR/$keyword"

    # Fix multi-line comments in JSON files by replacing newlines with spaces
    perl -0777 -p -i -e 's/"comment"\s*:\s*"((?:[^"\\]|\\.)*)"/"comment": "\1"/g; s/\n/ /g if /"comment":/' "$OUTPUT_DIR/$keyword"


    # Pretty-print all json files (this is also done upstream)

    if jq '.' "$OUTPUT_DIR/$keyword" > "$OUTPUT_DIR/$keyword.tmp"; then
        rm "$OUTPUT_DIR/$keyword" && mv "$OUTPUT_DIR/$keyword.tmp" "$OUTPUT_DIR/$keyword"
    else
        rm "$OUTPUT_DIR/$keyword.tmp"
    fi

    git add "$OUTPUT_DIR/$keyword"
done

git status .
