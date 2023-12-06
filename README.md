[![Build Status](https://img.shields.io/github/workflow/status/equinor/res2df/res2df)](https://github.com/equinor/res2df/actions?query=workflow%3Ares2df)
[![codecov](https://codecov.io/gh/equinor/res2df/graph/badge.svg?token=3sZBGGu5VG)](https://codecov.io/gh/equinor/res2df)
[![Python 3.8-3.10](https://img.shields.io/badge/python-3.8%20|%203.9%20|%203.10-blue.svg)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

# res2df

res2df is a Pandas DataFrame wrapper around resdata and opm.io, which
are used to access binary files outputted by reservoir simulators, 
or its input files --- or any other tool outputting to the same data format.

The reverse operation, from a Pandas DataFrame to reservoir simulator include files
(commonly given the extension ".inc", ".grdecl" etc.) is provided for some of the 
modules.

The package consists of a module pr. datatype, e.g. one module for summary
files (.UNSMRY), one for completion data etc.

There is a command line frontend for almost all functionality, called
`res2csv`, which converts the reservoir data to DataFrames, and then dumps
the dataframes to files in CSV format, and a similar `csv2res` for the
reverse operation.

For documentation, see <https://equinor.github.io/res2df/>

## License

This library is released under GPLv3.

## Copyright

The code is Copyright Equinor ASA 2019-2021.

Contributions without copyright transfer are welcome.
