import shutil
from pathlib import Path
from typing import Dict

import pytest

try:
    # pylint: disable=unused-import

    import ert.shared  # noqa
except ImportError:
    pytest.skip(
        "ERT is not installed. Skipping hook implementations.",
        allow_module_level=True,
    )

from ert.shared.plugins.plugin_manager import ErtPluginManager

import ecl2df.hook_implementations.jobs


@pytest.fixture(name="expected_jobs")
def fixture_expected_jobs(path_to_ecl2df: Path) -> Dict[str, Path]:
    """Dictionary of installed jobs with location to job configuration"""
    expected_job_names = [
        "ECL2CSV",
        "CSV2ECL",
    ]
    return {name: path_to_ecl2df / "config_jobs" / name for name in expected_job_names}


def test_hook_implementations(expected_jobs):
    """Test that the expected jobs can be found using an ERT plugin manager"""
    plugin_m = ErtPluginManager(plugins=[ecl2df.hook_implementations.jobs])

    installable_jobs = plugin_m.get_installable_jobs()
    for wf_name, wf_location in expected_jobs.items():
        assert wf_name in installable_jobs
        assert Path(installable_jobs[wf_name]).is_file()
        assert installable_jobs[wf_name].endswith(str(wf_location))

    assert set(installable_jobs.keys()) == set(expected_jobs.keys())

    expected_workflow_jobs = {}
    installable_workflow_jobs = plugin_m.get_installable_workflow_jobs()
    for wf_name, wf_location in expected_workflow_jobs.items():
        assert wf_name in installable_workflow_jobs
        assert installable_workflow_jobs[wf_name].endswith(wf_location)

    assert set(installable_workflow_jobs.keys()) == set(expected_workflow_jobs.keys())


def test_job_config_syntax(expected_jobs):
    """Check for syntax errors made in job configuration files"""
    for _, job_config in expected_jobs.items():
        # Check (loosely) that double-dashes are enclosed in quotes:
        for line in Path(job_config).read_text(encoding="utf8").splitlines():
            if not line.strip().startswith("--") and "--" in line:
                assert '"--' in line and " --" not in line


@pytest.mark.integration
def test_executables(expected_jobs):
    """Test executables listed in job configurations exist in $PATH"""
    for _, job_config in expected_jobs.items():
        executable = (
            Path(job_config).read_text(encoding="utf8").splitlines()[0].split()[1]
        )
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
