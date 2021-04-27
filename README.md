[![Build Status](https://img.shields.io/github/workflow/status/equinor/ecl2df/ecl2df)](https://github.com/equinor/ecl2df/actions?query=workflow%3Aecl2df)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/equinor/ecl2df.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/equinor/ecl2df/context:python)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/equinor/ecl2df.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/equinor/ecl2df/alerts/)
[![codecov](https://codecov.io/gh/equinor/ecl2df/branch/master/graph/badge.svg)](https://codecov.io/gh/equinor/ecl2df)
[![Python 3.6-3.9](https://img.shields.io/badge/python-3.6%20|%203.7%20|%203.8%20|%203.9-blue.svg)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

# ecl2df

ecl2df is a Pandas DataFrame wrapper around libecl and opm.io, which
are used to access binary files outputted by the reservoir simulator
Eclipse, or its input files --- or any other tool outputting to the same
data format.

The reverse operation, from a Pandas DataFrame to Eclipse include files,
is provided for some of the modules.

The package consists of a module pr. datatype, e.g. one module for summary
files (.UNSMRY), one for completion data etc.

There is a command line frontend for almost all functionality, called
`ecl2csv`, which converts the Eclipse data to DataFrames, and then dumps
the dataframes to files in CSV format, and a similar `csv2ecl` for the
reverse operation.

For documentation, see <https://equinor.github.io/ecl2df/>

## License

This library is released under GPLv3.

## Copyright

The code is Copyright Equinor ASA 2019-2021.

Contributions without copyright transfer are welcome.
