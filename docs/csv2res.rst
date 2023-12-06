csv2res
=======

Some of the modules inside res2df is able to write :term:`.DATA files<.DATA file>`
from dataframes (in the format dumped by res2df). This makes it possible
to produce :term:`.DATA files<.DATA file>` in any application that can write CSV files,
and use this tool to convert it into reservoir simulator files, or it can
facilitate operations/manipulations of an existing :term:`deck` using any tool
that can work on CSV files, by first running res2csv on an :term:`include file`,
transforming it, and writing back using csv2res.

Mandatory argument for csv2res is
always the submodule responsible, a CSV file, and
an ``--output`` option to specify which include file to write to.
If you want output to your terminal, use ``-`` as the output filename. Unless
you also specify the ``--keywords`` argument with a list of wanted keywords, all
supported keywords for a submodule which is also found in the CSV file provided,
will be dumped to an :term:`output file`.

.. argparse::
   :ref: res2df.csv2res.get_parser
   :prog: csv2res
