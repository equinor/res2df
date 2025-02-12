install_test_dependencies () {
  pip install -r test_requirements.txt
}

start_tests () {
  SHELLOPTS_BEFORE=$(set +o)
  set +e
  # (this script becomes flaky if set -e is active)
  source /prog/res/ecl/script/eclrun.bash
  eval "$SHELLOPTS_BEFORE"

  pytest --run-eclipse-simulator
}
