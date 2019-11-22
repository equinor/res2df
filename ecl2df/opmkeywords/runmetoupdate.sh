#!/bin/bash
#
# Run this to download a fresh copy of E100 keyword metadata from opm-common
#
# Remember to sync the keyword list here with the list in common.py

keywords="WCONPROD WCONHIST WCONINJE WCONINJH WELSPECS GRUPTREE GRUPNET COMPDAT COMPSEGS WELSEGS EQUIL FAULTS"

for keyword in $keywords; do
    firstletter=${keyword:0:1}
    wget https://raw.githubusercontent.com/OPM/opm-common/master/src/opm/parser/eclipse/share/keywords/000_Eclipse100/$firstletter/$keyword -O $keyword && git add $keyword
done

git status .
