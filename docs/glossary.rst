Glossary
========

.. glossary::

    .DATA files
        Inputs provided to reservoir simulators such as Eclipse or OPM Flow.
        Usually a .DATA file pointing to other include files. One .DATA file
        typically points to multiple include files. A data file is defined as
        a **full** data file if ?...TODO

    include files
        Files that provide inputs to reservoir simulators by using the INCLUDE statement
        in .DATA files. By convention, these files often have the extension .INC/.inc
        (generally) or .GRDECL/.grdecl (for files included into the grid section).

    reservoir simulator
        Reservoir simulators such as OPM Flow or Eclipse. 
