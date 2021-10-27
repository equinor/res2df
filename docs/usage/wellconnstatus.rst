wellconnstatus
--------------

Extracts connection status history for each compdat connection that is included
in the summary data on the form ``CPI:WELL,I,J,K``. CPI stands for connection
productivity index.

One line is added to the export every time a connection changes status. It
is ``OPEN`` when CPI>0 and ``SHUT`` when CPI=0. The earliest date for any connection
will be ``OPEN``, i.e a cell can not be ``SHUT`` before it has been OPEN. This means
that any cells that are always ``SHUT`` will be excluded.

The output data set is very sparse compared to the CPI summary data.

.. csv-table:: Well connection status example dataframe
   :file: well_connection_status.csv
   :header-rows: 1

The reason for extracting the well connection statuses from the summary data
is that it cannot always be extracted from parsing the schedule section like
the compdat module is doing. F.ex when ACTIONs are used to close/open connections
based on specific criterias.
