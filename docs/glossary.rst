Glossary
========

.. glossary::

    reservoir simulator
        Simulation of reservoir fields come in many forms, but for the purposes of 
        res2df we only consider simulators that take a :term:`deck` as input and produces
        :term:`output files <output file>` such `.UNSRMY`. This includes, OPM flow and Eclipse.

    .DATA file
        Input provided to reservoir simulators such as Eclipse or OPM Flow.
        Often a :term:`.DATA file` includes other :term:`include files <include file>` with the INCLUDE keyword.

    include file
        Files that provide inputs to reservoir simulators by using the INCLUDE statement
        in :term:`.DATA files <.DATA file>`. By convention, these files often have the extension .INC/.inc
        (generally) or .GRDECL/.grdecl (for files included into the grid section).

    deck
        Refers to inputs passed to reservoir simulators. It may be a :term:`.DATA file` and the
        include files it points to, or it may be a single or several include files.
        If a deck contains all the information (i.e., keywords) the simulator needs 
        to run the requested simulation, it is defined as complete. Otherwise it is incomplete.

    output file
        When a reservoir simulator runs, several files will be generated.
        These will have extensions such as .EGRID, .FEGRID, .UNSMRY, .GRID, .INIT, etc.
        See the opm flow manual Appendix D (https://opm-project.org/wp-content/uploads/2023/06/OPM_Flow_Reference_Manual_2023-04_Rev-0_Reduced.pdf)
