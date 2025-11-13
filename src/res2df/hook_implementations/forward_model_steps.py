import shutil
from collections.abc import Callable
from typing import Any, ParamSpec

P = ParamSpec("P")
try:
    from ert import (
        ForwardModelStepDocumentation,
        ForwardModelStepJSON,
        ForwardModelStepPlugin,
        ForwardModelStepValidationError,
    )
    from ert import plugin as ert_plugin
except ModuleNotFoundError:
    # ert is not installed, use dummy/transparent function decorator:
    def ert_plugin(name: str = "") -> Callable[[Callable[P, Any]], Callable[P, Any]]:
        def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
            return func

        return decorator

    class ForwardModelStepDocumentation:  # type: ignore[no-redef]
        pass

    class ForwardModelStepJSON:  # type: ignore[no-redef]
        pass

    class ForwardModelStepPlugin:  # type: ignore[no-redef]
        pass

    class ForwardModelStepValidationError:  # type: ignore[no-redef]
        pass


class Res2Csv(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="RES2CSV",
            command=[
                shutil.which("res2csv"),
                "<SUBCOMMAND>",
                "--verbose",
                "--output",
                "<OUTPUT>",
                *[f"<XARG{num + 1}>" for num in range(10)],
                "--",
                "<ECLBASE>",
            ],
            default_mapping={f"<XARG{num + 1}>": "" for num in range(10)},
        )

    def validate_pre_experiment(self, fm_json: ForwardModelStepJSON) -> None:
        if fm_json["argList"][0] == "<SUBCOMMAND>":
            raise ForwardModelStepValidationError(
                "You must supply a value for SUBCOMMAND to RES2CSV"
            )
        if fm_json["argList"][3] == "<OUTPUT>":
            raise ForwardModelStepValidationError(
                "You must supply a value for OUTPUT to RES2CSV"
            )

    @staticmethod
    def documentation() -> ForwardModelStepDocumentation | None:
        return ForwardModelStepDocumentation(
            description="""Convert reservoir simulator input and output files into CSV
files, with the command line utility ``res2csv``. Run ``res2csv --help`` to see
which subcommands are supported.

For supplying options to subcommands, you can use the arguments ``<XARGn>``
where ``n`` goes from 1 to 10.

For more documentation, see https://equinor.github.io/res2df/.
""",
            category="utility.eclipse",
            examples="""Outputting the EQUIL data from a .DATA file. This is implicitly
supplied in ERT configs::

   FORWARD_MODEL RES2CSV(<SUBCOMMAND>=equil, <OUTPUT>=equil.csv)

For a yearly summary export of the realization, options have to be supplied
with the XARG options::

  FORWARD_MODEL RES2CSV(<SUBCOMMAND>=summary, \
    <OUTPUT>=yearly.csv, <XARG1>="--time_index", <XARG2>="yearly")

The quotes around double-dashed options are critical to avoid ERT taking for a
comment. For more options, use ``<XARG3>`` etc.
""",
        )


class Csv2Res(ForwardModelStepPlugin):
    def __init__(self) -> None:
        super().__init__(
            name="CSV2RES",
            command=[
                shutil.which("csv2res"),
                "<SUBCOMMAND>",
                "--verbose",
                "--output",
                "<OUTPUT>",
                "<CSVFILE>",
            ],
        )

    def validate_pre_experiment(self, fm_json: ForwardModelStepJSON) -> None:
        if fm_json["argList"][0] == "<SUBCOMMAND>":
            raise ForwardModelStepValidationError(
                "You must supply a value for SUBCOMMAND to CSV2RES"
            )
        if fm_json["argList"][3] == "<OUTPUT>":
            raise ForwardModelStepValidationError(
                "You must supply a value for OUTPUT to CSV2RES"
            )
        if fm_json["argList"][4] == "<CSVFILE>":
            raise ForwardModelStepValidationError(
                "You must supply a value for CSVFILE to CSV2RES"
            )

    @staticmethod
    def documentation() -> ForwardModelStepDocumentation | None:
        return ForwardModelStepDocumentation(
            description="""Convert CSV files into include files. Uses the command
line utility ``csv2res``. Run ``csv2res --help`` to see which subcommands are supported.
No options other than the output file is possible when used directly as a forward model.
When writing synthetic summary files, the ECLBASE with no filename suffix is expected
as the OUTPUT argument.""",
            category="utility.eclipse",
            examples=(
                "``FORWARD_MODEL "
                "CSV2RES(<SUBCOMMAND>=equil, <CSVFILE>=equil.csv, "
                "<OUTPUT>=eclipse/include/equil.inc)``"
                "CSV2RES(<SUBCOMMAND>=summary, <CSVFILE>=summary-monthly.csv, "
                "<OUTPUT>=eclipse/model/MONTHLYSUMMARY)``"
            ),
        )


@ert_plugin(name="RES2CSV")
def installable_forward_model_steps() -> list[type[ForwardModelStepPlugin]]:
    return [Res2Csv, Csv2Res]
