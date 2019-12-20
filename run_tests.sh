#!/bin/bash

function usage {
  echo "Usage: $0 [OPTION]..."
  echo "Run python-muranoclient's test suite(s)"
  echo ""
  echo "  -p, --pep8               Just run pep8"
  echo "  -h, --help               Print this usage message"
  echo "  -V, --virtual-env        Always use virtualenv.  Install automatically if not present"
  echo "  -N, --no-virtual-env     Don't use virtualenv.  Run tests in local environment"
  echo "  -f, --force              Force a clean re-build of the virtual environment. Useful when dependencies have been added."
  echo "  -u, --update             Update the virtual environment with any newer package versions"
  echo ""
  echo "This script is deprecated and currently retained for compatibility."
  echo 'You can run the full test suite for multiple environments by running "tox".'
  echo 'You can run tests for only python 3.7 by running "tox -e py37", or run only'
  echo 'the pep8 tests with "tox -e pep8".'
  exit
}

just_pep8=0
always_venv=0
never_venv=0
wrapper=
update=0
force=0

export NOSE_WITH_OPENSTACK=1
export NOSE_OPENSTACK_COLOR=1
export NOSE_OPENSTACK_RED=0.05
export NOSE_OPENSTACK_YELLOW=0.025
export NOSE_OPENSTACK_SHOW_ELAPSED=1
export NOSE_OPENSTACK_STDOUT=1


function process_option {
  case "$1" in
    -h|--help) usage;;
    -p|--pep8) let just_pep8=1;;
    -V|--virtual-env) let always_venv=1; let never_venv=0;;
    -f|--force) let force=1;;
    -u|--update) update=1;;
    -N|--no-virtual-env) let always_venv=0; let never_venv=1;;
  esac
}

for arg in "$@"; do
  process_option $arg
done

function run_tests {
  # Cleanup *pyc and *pyo
  ${wrapper} find . -type f -name "*.py[c|o]" -delete
  # Just run the test suites in current environment
  ${wrapper} $NOSETESTS
}

function run_pep8 {
  echo "Running pep8 ..."
  PEP8_EXCLUDE=".venv,.tox,dist,doc,openstack,build"
  PEP8_OPTIONS="--exclude=$PEP8_EXCLUDE --repeat --select=H402"
  PEP8_IGNORE="--ignore=E125,E126,E711,E712"
  PEP8_INCLUDE="."
  pep8 $PEP8_OPTIONS $PEP8_INCLUDE $PEP8_IGNORE
}

NOSETESTS="nosetests $noseopts $noseargs"

if [ $never_venv -eq 0 ]
then
  # Remove the virtual environment if --force used
  if [ $force -eq 1 ]; then
    echo "Cleaning virtualenv..."
    rm -rf ${venv}
  fi
  if [ $update -eq 1 ]; then
    echo "Updating virtualenv..."
    python tools/install_venv.py
  fi
  if [ -e ${venv} ]; then
    wrapper="${with_venv}"
  else
    if [ $always_venv -eq 1 ]; then
      # Automatically install the virtualenv
      python tools/install_venv.py
      wrapper="${with_venv}"
    else
      echo -e "No virtual environment found...create one? (Y/n) \c"
      read use_ve
      if [ "x$use_ve" = "xY" -o "x$use_ve" = "x" -o "x$use_ve" = "xy" ]; then
        # Install the virtualenv and run the test suite in it
        python tools/install_venv.py
		    wrapper=${with_venv}
      fi
    fi
  fi
fi

if [ $just_pep8 -eq 1 ]; then
  run_pep8
  exit
fi

run_tests || exit

run_pep8

