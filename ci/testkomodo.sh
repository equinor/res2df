install_test_dependencies () {
  pip install -r test_requirements.txt
}

start_tests () {
  source /prog/res/ecl/script/eclrun.bash
  pytest --run-eclipse-simulator
}
