res2csv
=======

Most of the functionality in res2df is exposed to the command line through
the script *res2csv*. The first argument to this script is always
the submodule (subcommand) from which you want functionality. Mandatory argument is
always a :term:`.DATA file` or sometimes individual
:term:`include files <include file>`, and there is usually an ``--output``
option to specify which file to dump the CSV to.
If you want output to your terminal, use ``-`` as the output filename.

.. argparse::
   :ref: res2df.res2csv.get_parser
   :prog: res2csv
