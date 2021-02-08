ecl2csv
=======

Most of the functionality in ecl2df is exposed to the command line through
the script *ecl2csv*. The first argument to this script is always
the submodule (subcommand) from which you want functionality. Mandatory argument is
always an Eclipse deck or sometimes individual Eclipse include files, and
there is usually an ``--output`` option to specify which file to dump
the CSV to. If you want output to your terminal, use ``-`` as the output filename.

.. argparse::
   :ref: ecl2df.ecl2csv.get_parser
   :prog: ecl2csv
