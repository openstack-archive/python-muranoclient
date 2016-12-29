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
from muranoclient.v1 import packages

import mock
from osc_lib import exceptions as exc
from osc_lib import utils

FIXTURE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'fixture_data'))

COLUMNS = ['Id', 'Name', 'Fully_qualified_name', 'Author', 'Active',
           'Is public', 'Type', 'Version']

DATA = {
    'class_definitions': ['com.example.apache.ApacheHttpServer'],
    'updated': '2016-09-20T06:23:45.000000',
    'description': 'Test description.\n',
    'created': '2016-09-20T06:23:15.000000',
    'author': 'Mirantis, Inc',
    'enabled': True,
    'owner_id': 'a203405ea871484a940850d6c0b8dfd9',
    'tags': ['Server', 'WebServer', 'Apache', 'HTTP', 'HTML'],
    'is_public': False,
    'fully_qualified_name': 'com.example.apache.ApacheHttpServer',
    'type': 'Application',
    'id': '46860070-5f8a-4936-96e8-d7b89e5187d7',
    'categories': [],
    'name': 'Apache HTTP Server'
}


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


class TestPackageList(TestPackage):

    def setUp(self):
        super(TestPackageList, self).setUp()
        self.cmd = osc_pkg.ListPackages(self.app, None)
        self.package_mock.filter.return_value = \
            [packages.Package(None, DATA)]
        utils.get_dict_properties = mock.MagicMock(return_value='')

    def test_stack_list_defaults(self):
        arglist = []
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.package_mock.filter.assert_called_with(
            include_disabled=False,
            owned=False)
        self.assertEqual(COLUMNS, columns)

    def test_stack_list_with_limit(self):
        arglist = ['--limit', '10']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.package_mock.filter.assert_called_with(
            include_disabled=False,
            limit=10,
            owned=False)

    def test_stack_list_with_marker(self):
        arglist = ['--marker', '12345']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.package_mock.filter.assert_called_with(
            include_disabled=False,
            marker='12345',
            owned=False)

    def test_stack_list_with_name(self):
        arglist = ['--name', 'mysql']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.package_mock.filter.assert_called_with(
            include_disabled=False,
            name='mysql',
            owned=False)

    def test_stack_list_with_fqn(self):
        arglist = ['--fqn', 'mysql']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.package_mock.filter.assert_called_with(
            include_disabled=False,
            fqn='mysql',
            owned=False)


class TestPackageDelete(TestPackage):
    def setUp(self):
        super(TestPackageDelete, self).setUp()
        self.package_mock.delete.return_value = None
        self.package_mock.filter.return_value = \
            [packages.Package(None, DATA)]

        # Command to test
        self.cmd = osc_pkg.DeletePackage(self.app, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_package_delete(self, mock_util):
        arglist = ['fake1']
        verifylist = [('id', ['fake1'])]

        mock_util.return_value = ('1234', 'Core library',
                                  'io.murano', 'murano.io', '',
                                  'True', 'Library', '0.0.0'
                                  )

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        self.assertEqual(COLUMNS, columns)

        # Check that data is correct
        expected_data = [('1234', 'Core library', 'io.murano',
                          'murano.io', '', 'True', 'Library', '0.0.0')]
        self.assertEqual(expected_data, data)
