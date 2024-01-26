install_test_dependencies () {
  pip install -r test_requirements.txt
}

install_package () {
  pip install .[tests,docs]
}

start_tests () {
  pytest --run-eclipse-simulator
}
