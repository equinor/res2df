Glossary
========

.. glossary::

    reservoir simulator
        Reservoir simulators such as OPM Flow or Eclipse. 

    .DATA file
        Inputs provided to reservoir simulators such as Eclipse or OPM Flow.
        Usually a .DATA file pointing to other include files. One .DATA file
        typically points to multiple include files. A data file is defined as
        a **full** data file if ?...TODO

    include file
        Files that provide inputs to reservoir simulators by using the INCLUDE statement
        in .DATA files. By convention, these files often have the extension .INC/.inc
        (generally) or .GRDECL/.grdecl (for files included into the grid section).

    reservoir simulator output file
        When a reservoir simulator runs, several files will be generated.
        These will have extensions such as .EGRID, .FEGRID, .UNSMRY, .GRID, .INIT, etc.
        See the opm flow manual Appendix D (https://opm-project.org/wp-content/uploads/2023/06/OPM_Flow_Reference_Manual_2023-04_Rev-0_Reduced.pdf)
