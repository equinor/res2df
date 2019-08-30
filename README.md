# ecl2df [![Build Status](https://travis-ci.com/equinor/ecl2df.svg?branch=master)](https://travis-ci.com/equinor/ecl2df) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/fceedc1ee9c946aa85bf60f39ec8962a)](https://www.codacy.com/app/berland/ecl2df?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=equinor/ecl2df&amp;utm_campaign=Badge_Grade)

ecl2df is a Pandas DataFrame wrapper around libecl and sunbeam, which
are used to access binary files outputted by the reservoir simulator
Eclipse, or its input files --- or any other tool outputting to the same
data format. 

The package consists of a module pr. datatype, e.g. one module for summary 
files (.UNSMRY), one for completion data etc.

There is a command line frontend for almost all functionality, called
`ecl2csv`, which converts the Eclipse data to DataFrames, and then dumps
the dataframes to files in CSV format.

For documentation, see <https://equinor.github.io/ecl2df/>


## License

This library is released under GPLv3.

## Copyright

The code is Copyright Equinor ASA 2019.

Contributions without copyright transfer are welcome.
