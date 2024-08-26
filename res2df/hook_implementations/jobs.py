import importlib
import sys
from pathlib import Path

try:
    from ert import plugin as ert_plugin  # type: ignore
except ModuleNotFoundError:
    # ert is not installed - use dummy/transparent function decorator:
    def ert_plugin(name: str = ""):
        def decorator(func):
            return func

        return decorator


def _get_jobs_from_directory(directory):
    resource_directory = Path(sys.modules["res2df"].__file__).parent / directory

    all_files = [
        resource_directory / filename
        for filename in resource_directory.glob("*")
        if (resource_directory / filename).exists()
    ]
    return {path.name: str(path) for path in all_files}


@ert_plugin(name="res2df")
def installable_jobs():
    return _get_jobs_from_directory("config_jobs")


def _get_module_variable_if_exists(module_name, variable_name, default=""):
    try:
        script_module = importlib.import_module(module_name)
    except ImportError:
        return default

    return getattr(script_module, variable_name, default)


@ert_plugin(name="res2df")
def job_documentation(job_name):
    res2df_jobs = set(installable_jobs().data.keys())
    if job_name not in res2df_jobs:
        return None

    module_name = f"res2df.{job_name.lower()}"

    description = _get_module_variable_if_exists(
        module_name=module_name, variable_name="DESCRIPTION"
    )
    examples = _get_module_variable_if_exists(
        module_name=module_name, variable_name="EXAMPLES"
    )
    category = _get_module_variable_if_exists(
        module_name=module_name, variable_name="CATEGORY", default="other"
    )

    return {
        "description": description,
        "examples": examples,
        "category": category,
    }
