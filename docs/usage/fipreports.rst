fipreports
----------

fipreports is a parser for the PRT output file, extracting data
from these tables:

.. literalinclude:: fipreports-example.txt

This table found in a PRT file will be parsed to the following dataframe:

..
  Generated with res2csv fipreports -v --fipname FIPZON fipreports-example.PRT -o fipreports-example.csv
  Date added manually

.. csv-table:: FIPZON table from PRT file
   :file: fipreports-example.csv
   :header-rows: 1

In this particular example, ``FIPZON`` was selected explicitly, either using the command line client or the Python API
through an option to the :func:`res2df.fipreports.df` function.

Using this module is easiest through ``res2csv fipreports``.





