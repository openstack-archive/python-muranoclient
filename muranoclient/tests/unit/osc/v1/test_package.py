#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import six
import sys
import tempfile

from testtools import matchers

from muranoclient.osc.v1 import package as osc_pkg
from muranoclient.tests.unit.osc.v1 import fakes

from osc_lib import exceptions as exc

FIXTURE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'fixture_data'))


class TestPackage(fakes.TestApplicationCatalog):
    def setUp(self):
        super(TestPackage, self).setUp()
        self.package_mock = self.app.client_manager.application_catalog.\
            packages
        self.package_mock.reset_mock()


class TestCreatePackage(TestPackage):
    def setUp(self):
        super(TestCreatePackage, self).setUp()

        # Command to test
        self.cmd = osc_pkg.CreatePackage(self.app, None)

    def test_create_package_without_args(self):
        arglist = []
        parsed_args = self.check_parser(self.cmd, arglist, [])
        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)
        self.assertEqual('Provide --template for a HOT-based package, OR at '
                         'least --classes-dir for a MuranoPL-based package',
                         str(error))

    def test_create_package_template_and_classes_args(self):
        heat_template = os.path.join(FIXTURE_DIR, 'heat-template.yaml')
        classes_dir = os.path.join(FIXTURE_DIR, 'test-app', 'Classes')
        arglist = ['--template', heat_template, '--classes-dir', classes_dir]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)
        self.assertEqual('Provide --template for a HOT-based package, OR'
                         ' --classes-dir for a MuranoPL-based package',
                         str(error))

    def test_create_hot_based_package(self):
        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name
            heat_template = os.path.join(FIXTURE_DIR, 'heat-template.yaml')
            logo = os.path.join(FIXTURE_DIR, 'logo.png')
            arglist = ['--template', heat_template, '--output', RESULT_PACKAGE,
                       '-l', logo]
            parsed_args = self.check_parser(self.cmd, arglist, [])
            orig = sys.stdout
            try:
                sys.stdout = six.StringIO()
                self.cmd.take_action(parsed_args)
            finally:
                stdout = sys.stdout.getvalue()
                sys.stdout.close()
                sys.stdout = orig
            matchers.MatchesRegex(stdout,
                                  "Application package "
                                  "is available at {0}".format(RESULT_PACKAGE))

    def test_create_mpl_package(self):
        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name
            classes_dir = os.path.join(FIXTURE_DIR, 'test-app', 'Classes')
            resources_dir = os.path.join(FIXTURE_DIR, 'test-app', 'Resources')
            ui = os.path.join(FIXTURE_DIR, 'test-app', 'ui.yaml')
            arglist = ['-c', classes_dir, '-r', resources_dir,
                       '-u', ui, '-o', RESULT_PACKAGE]
            parsed_args = self.check_parser(self.cmd, arglist, [])
            orig = sys.stdout
            try:
                sys.stdout = six.StringIO()
                self.cmd.take_action(parsed_args)
            finally:
                stdout = sys.stdout.getvalue()
                sys.stdout.close()
                sys.stdout = orig
            matchers.MatchesRegex(stdout,
                                  "Application package "
                                  "is available at {0}".format(RESULT_PACKAGE))
