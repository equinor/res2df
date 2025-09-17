#!/bin/bash
#
# Run this to download a fresh copy of E100 keyword metadata from opm-common

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
    wget https://raw.githubusercontent.com/OPM/opm-common/master/opm/input/eclipse/share/keywords/000_Eclipse100/$firstletter/$keyword -O $keyword

    # Assume that the presence of num_tables in some keywords is sort of a bug:
    perl -p -i -e 's/num_tables/size/g' $keyword

    # Fix multi-line comments in JSON files by replacing newlines with spaces
    perl -0777 -p -i -e 's/"comment"\s*:\s*"((?:[^"\\]|\\.)*)"/"comment": "\1"/g; s/\n/ /g if /"comment":/' "$keyword"


    # Pretty-print all json files (this is also done upstream)

    if jq '.' "$keyword" > "$keyword.tmp"; then
        rm "$keyword" && mv "$keyword.tmp" "$keyword"
    else
        rm "$keyword.tmp"
    fi

    git add $keyword
done

git status .
