import importlib
import os
from pkg_resources import resource_filename

from ert_shared.plugins.plugin_manager import hook_implementation
from ert_shared.plugins.plugin_response import plugin_response


def _get_jobs_from_directory(directory):
    resource_directory = resource_filename("ecl2df", directory)

    all_files = [
        os.path.join(resource_directory, f)
        for f in os.listdir(resource_directory)
        if os.path.isfile(os.path.join(resource_directory, f))
    ]
    return {os.path.basename(path): path for path in all_files}


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

    module_name = "ecl2df.{job_name}".format(job_name=job_name.lower())

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
