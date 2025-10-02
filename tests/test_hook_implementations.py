import pytest

try:
    import ert  # noqa: F401
except ImportError:
    pytest.skip(
        "ERT is not installed. Skipping hook implementations.",
        allow_module_level=True,
    )

from ert.plugins.plugin_manager import ErtPluginManager

import res2df.hook_implementations.forward_model_steps


def test_hooks_are_installed_in_erts_plugin_manager():
    plugin_m = ErtPluginManager(
        plugins=[res2df.hook_implementations.forward_model_steps]
    )
    available_fm_steps = [step().name for step in plugin_m.forward_model_steps]
    assert "CSV2RES" in available_fm_steps
    assert "RES2CSV" in available_fm_steps


def test_hook_implementations_have_docs_installed():
    plugin_m = ErtPluginManager(
        plugins=[res2df.hook_implementations.forward_model_steps]
    )
    for step_doc in [step().documentation() for step in plugin_m.forward_model_steps]:
        assert step_doc.description
        assert step_doc.category
        assert step_doc.examples
