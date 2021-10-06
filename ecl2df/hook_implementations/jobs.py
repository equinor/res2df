import importlib
from pathlib import Path

from pkg_resources import resource_filename

try:
    from ert_shared.plugins.plugin_manager import hook_implementation
    from ert_shared.plugins.plugin_response import plugin_response
except ModuleNotFoundError:
    # ert is not installed - use dummy/transparent function decorators.
    def hook_implementation(func):
        return func

    def plugin_response(plugin_name):  # pylint: disable=unused-argument
        def decorator(func):
            return func

        return decorator


def _get_jobs_from_directory(directory):
    resource_directory = Path(resource_filename("ecl2df", directory))

    all_files = [
        resource_directory / filename
        for filename in resource_directory.glob("*")
        if (resource_directory / filename).exists()
    ]
    return {path.name: str(path) for path in all_files}


@hook_implementation
@plugin_response(plugin_name="ecl2df")
def installable_jobs():
    return _get_jobs_from_directory("config_jobs")


def _get_module_variable_if_exists(module_name, variable_name, default=""):
    try:
        script_module = importlib.import_module(module_name)
    except ImportError:
        return default

    return getattr(script_module, variable_name, default)


@hook_implementation
@plugin_response(plugin_name="ecl2df")
def job_documentation(job_name):
    ecl2df_jobs = set(installable_jobs().data.keys())
    if job_name not in ecl2df_jobs:
        return None

    module_name = f"ecl2df.{job_name.lower()}"

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
