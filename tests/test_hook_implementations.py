import shutil
from pathlib import Path

import pytest

try:
    # pylint: disable=unused-import

    import ert_shared  # noqa
except ImportError:
    pytest.skip(
        "ERT is not installed. Skipping hook implementations.",
        allow_module_level=True,
    )

from ert_shared.plugins.plugin_manager import ErtPluginManager

import ecl2df.hook_implementations.jobs

EXPECTED_JOBS = {
    "ECL2CSV": "ecl2df/config_jobs/ECL2CSV",
    "CSV2ECL": "ecl2df/config_jobs/CSV2ECL",
}


def test_hook_implementations():
    """Test that the expected jobs can be found using an ERT plugin manager"""
    plugin_m = ErtPluginManager(plugins=[ecl2df.hook_implementations.jobs])

    installable_jobs = plugin_m.get_installable_jobs()
    for wf_name, wf_location in EXPECTED_JOBS.items():
        assert wf_name in installable_jobs
        assert installable_jobs[wf_name].endswith(wf_location)
        assert Path(installable_jobs[wf_name]).is_file()

    assert set(installable_jobs.keys()) == set(EXPECTED_JOBS.keys())

    expected_workflow_jobs = {}
    installable_workflow_jobs = plugin_m.get_installable_workflow_jobs()
    for wf_name, wf_location in expected_workflow_jobs.items():
        assert wf_name in installable_workflow_jobs
        assert installable_workflow_jobs[wf_name].endswith(wf_location)

    assert set(installable_workflow_jobs.keys()) == set(expected_workflow_jobs.keys())


def test_job_config_syntax():
    """Check for syntax errors made in job configuration files"""
    src_path = Path(__file__).parent.parent
    for _, job_config in EXPECTED_JOBS.items():
        # Check (loosely) that double-dashes are enclosed in quotes:
        with open(src_path / job_config) as f_handle:
            for line in f_handle.readlines():
                if not line.strip().startswith("--") and "--" in line:
                    assert '"--' in line and " --" not in line


@pytest.mark.integration
def test_executables():
    """Test executables listed in job configurations exist in $PATH"""
    src_path = Path(__file__).parent.parent
    for _, job_config in EXPECTED_JOBS.items():
        with open(src_path / job_config) as f_handle:
            executable = f_handle.readlines()[0].split()[1]
            assert shutil.which(executable)


def test_hook_implementations_job_docs():
    """Test extracting docs from ERT hooks"""
    plugin_m = ErtPluginManager(plugins=[ecl2df.hook_implementations.jobs])

    installable_jobs = plugin_m.get_installable_jobs()

    docs = plugin_m.get_documentation_for_jobs()

    assert set(docs.keys()) == set(installable_jobs.keys())

    for job_name in installable_jobs.keys():
        print(job_name)
        assert docs[job_name]["description"] != ""
        assert docs[job_name]["category"] != "other"
