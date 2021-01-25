#!/bin/bash
#
# Run this to download a fresh copy of E100 keyword metadata from opm-common

# Remember to sync the keyword list here with the list in common.py
keywords="
COMPDAT
COMPSEGS
DENSITY
EQLDIMS
EQUIL
FAULTS
GRUPNET
GRUPTREE
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
WCONHIST
WCONINJE
WCONINJH
WCONPROD
WELOPEN
WELSEGS
WELSPECS
WSEGAICD
WSEGSICD
WSEGVALV
"

for keyword in $keywords; do
    firstletter=${keyword:0:1}
    wget https://raw.githubusercontent.com/OPM/opm-common/master/src/opm/parser/eclipse/share/keywords/000_Eclipse100/$firstletter/$keyword -O $keyword && git add $keyword

    # Assume that the presence of num_tables in some keywords is sort of a bug:
    perl -p -i -e 's/num_tables/size/g' $keyword

    # Pretty-print all json files (this is also done upstream)
    jq < $keyword . > $keyword.tmp && rm $keyword && mv $keyword.tmp $keyword 
done

git status .
