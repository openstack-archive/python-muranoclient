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

import io
import json
import os
import shutil
import sys
import tempfile
from unittest import mock

from testtools import matchers

from muranoclient.common import exceptions as common_exceptions
from muranoclient.common import utils as mc_utils
from muranoclient.osc.v1 import package as osc_pkg
from muranoclient.tests.unit.osc.v1 import fakes
from muranoclient.tests.unit import test_utils
from muranoclient.v1 import packages

from osc_lib import exceptions as exc
from osc_lib import utils
import requests_mock

make_pkg = test_utils.make_pkg

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
                sys.stdout = io.StringIO()
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
                sys.stdout = io.StringIO()
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

    def test_package_list_defaults(self):
        arglist = []
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.package_mock.filter.assert_called_with(
            include_disabled=False,
            owned=False)
        self.assertEqual(COLUMNS, columns)

    def test_package_list_with_limit(self):
        arglist = ['--limit', '10']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.package_mock.filter.assert_called_with(
            include_disabled=False,
            limit=10,
            owned=False)

    def test_package_list_with_marker(self):
        arglist = ['--marker', '12345']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.package_mock.filter.assert_called_with(
            include_disabled=False,
            marker='12345',
            owned=False)

    def test_package_list_with_name(self):
        arglist = ['--name', 'mysql']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.package_mock.filter.assert_called_with(
            include_disabled=False,
            name='mysql',
            owned=False)

    def test_package_list_with_fqn(self):
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


class TestPackageImport(TestPackage):
    def setUp(self):
        super(TestPackageImport, self).setUp()
        self.package_mock.filter.return_value = \
            [packages.Package(None, DATA)]

        # Command to test
        self.cmd = osc_pkg.ImportPackage(self.app, None)

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import(self, from_file):
        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name
            categories = ['Cat1', 'Cat2 with space']

            pkg = make_pkg({'FullName': RESULT_PACKAGE})
            from_file.return_value = mc_utils.Package(mc_utils.File(pkg))

            arglist = [RESULT_PACKAGE, '--categories',
                       categories, '--is-public']
            parsed_args = self.check_parser(self.cmd, arglist, [])
            self.cmd.take_action(parsed_args)

            self.package_mock.create.assert_called_once_with({
                'categories': [categories],
                'is_public': True
            }, {RESULT_PACKAGE: mock.ANY},)

    def _test_conflict(self,
                       packages, from_file, raw_input_mock,
                       input_action, exists_action=''):
        packages.create = mock.MagicMock(
            side_effect=[common_exceptions.HTTPConflict("Conflict"), None])

        packages.filter.return_value = [mock.Mock(id='test_id')]

        raw_input_mock.return_value = input_action
        with tempfile.NamedTemporaryFile() as f:
            pkg = make_pkg({'FullName': f.name})
            from_file.return_value = mc_utils.Package(mc_utils.File(pkg))
            if exists_action:
                arglist = [f.name, '--exists-action', exists_action]
            else:
                arglist = [f.name]
            parsed_args = self.check_parser(self.cmd, arglist, [])
            self.cmd.take_action(parsed_args)

            return f.name

    @mock.patch('builtins.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_skip(self, from_file, raw_input_mock):

        name = self._test_conflict(
            self.package_mock,
            from_file,
            raw_input_mock,
            's',
        )

        self.package_mock.create.assert_called_once_with({
            'is_public': False,
        }, {name: mock.ANY},)

    @mock.patch('builtins.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_skip_ea(self, from_file, raw_input_mock):

        name = self._test_conflict(
            self.package_mock,
            from_file,
            raw_input_mock,
            '',
            exists_action='s',
        )

        self.package_mock.create.assert_called_once_with({
            'is_public': False,
        }, {name: mock.ANY},)
        self.assertFalse(raw_input_mock.called)

    @mock.patch('builtins.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_abort(self, from_file, raw_input_mock):

        self.assertRaises(SystemExit, self._test_conflict,
                          self.package_mock,
                          from_file,
                          raw_input_mock,
                          'a',
                          )

        self.package_mock.create.assert_called_once_with({
            'is_public': False,
        }, mock.ANY,)

    @mock.patch('builtins.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_abort_ea(self,
                                              from_file, raw_input_mock):

        self.assertRaises(SystemExit, self._test_conflict,
                          self.package_mock,
                          from_file,
                          raw_input_mock,
                          '',
                          exists_action='a',
                          )

        self.package_mock.create.assert_called_once_with({
            'is_public': False,
        }, mock.ANY,)
        self.assertFalse(raw_input_mock.called)

    @mock.patch('builtins.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_update(self, from_file, raw_input_mock):

        name = self._test_conflict(
            self.package_mock,
            from_file,
            raw_input_mock,
            'u',
        )

        self.assertEqual(2, self.package_mock.create.call_count)
        self.package_mock.delete.assert_called_once_with('test_id')

        self.package_mock.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {name: mock.ANY},),
                mock.call({'is_public': False}, {name: mock.ANY},)
            ], any_order=True,
        )

    @mock.patch('builtins.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_update_ea(self,
                                               from_file, raw_input_mock):

        name = self._test_conflict(
            self.package_mock,
            from_file,
            raw_input_mock,
            '',
            exists_action='u',
        )

        self.assertEqual(2, self.package_mock.create.call_count)
        self.package_mock.delete.assert_called_once_with('test_id')

        self.package_mock.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {name: mock.ANY},),
                mock.call({'is_public': False}, {name: mock.ANY},)
            ], any_order=True,
        )
        self.assertFalse(raw_input_mock.called)

    def _test_conflict_dep(self,
                           packages, from_file,
                           dep_exists_action=''):
        packages.create = mock.MagicMock(
            side_effect=[common_exceptions.HTTPConflict("Conflict"),
                         common_exceptions.HTTPConflict("Conflict"),
                         None])

        packages.filter.return_value = [mock.Mock(id='test_id')]

        pkg1 = make_pkg(
            {'FullName': 'first_app', 'Require': {'second_app': '1.0'}, })
        pkg2 = make_pkg({'FullName': 'second_app', })

        def side_effect(name):
            if 'first_app' in name:
                return mc_utils.Package(mc_utils.File(pkg1))
            if 'second_app' in name:
                return mc_utils.Package(mc_utils.File(pkg2))

        from_file.side_effect = side_effect

        arglist = ['first_app', '--exists-action', 's',
                   '--dep-exists-action', dep_exists_action]

        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_dep_skip_ea(self, from_file):
        self._test_conflict_dep(
            self.package_mock,
            from_file,
            dep_exists_action='s',
        )

        self.assertEqual(2, self.package_mock.create.call_count)
        self.package_mock.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
            ], any_order=True,
        )

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_dep_abort_ea(self, from_file):
        self.assertRaises(SystemExit, self._test_conflict_dep,
                          self.package_mock,
                          from_file,
                          dep_exists_action='a',
                          )

        self.package_mock.create.assert_called_with({
            'is_public': False,
        }, {'second_app': mock.ANY},)

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_dep_update_ea(self, from_file):
        self._test_conflict_dep(
            self.package_mock,
            from_file,
            dep_exists_action='u',
        )

        self.assertGreater(self.package_mock.create.call_count, 2)
        self.assertLess(self.package_mock.create.call_count, 5)

        self.assertTrue(self.package_mock.delete.called)

        self.package_mock.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
            ], any_order=True,
        )

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_no_categories(self, from_file):
        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name
            pkg = make_pkg({'FullName': RESULT_PACKAGE})
            from_file.return_value = mc_utils.Package(mc_utils.File(pkg))

            arglist = [RESULT_PACKAGE]
            parsed_args = self.check_parser(self.cmd, arglist, [])
            self.cmd.take_action(parsed_args)

            self.package_mock.create.assert_called_once_with(
                {'is_public': False},
                {RESULT_PACKAGE: mock.ANY},
            )

    @requests_mock.mock()
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_url(self, rm, from_file):
        filename = "http://127.0.0.1/test_package.zip"

        pkg = make_pkg({'FullName': 'test_package'})
        from_file.return_value = mc_utils.Package(mc_utils.File(pkg))

        rm.get(filename, body=make_pkg({'FullName': 'test_package'}))

        arglist = [filename]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.package_mock.create.assert_called_once_with(
            {'is_public': False},
            {'test_package': mock.ANY},
        )

    @requests_mock.mock()
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_by_name(self, rm, from_file):
        filename = "io.test.apps.test_application"
        murano_repo_url = "http://127.0.0.1"

        pkg = make_pkg({'FullName': filename})
        from_file.return_value = mc_utils.Package(mc_utils.File(pkg))

        rm.get(murano_repo_url + '/apps/' + filename + '.zip',
               body=make_pkg({'FullName': 'first_app'}))

        arglist = [filename, '--murano-repo-url', murano_repo_url]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.assertTrue(self.package_mock.create.called)
        self.package_mock.create.assert_called_once_with(
            {'is_public': False},
            {filename: mock.ANY},
        )

    @requests_mock.mock()
    def test_package_import_multiple(self, rm):
        filename = ["io.test.apps.test_application",
                    "http://127.0.0.1/test_app2.zip", ]
        murano_repo_url = "http://127.0.0.1"

        rm.get(murano_repo_url + '/apps/' + filename[0] + '.zip',
               body=make_pkg({'FullName': 'first_app'}))

        rm.get(filename[1],
               body=make_pkg({'FullName': 'second_app'}))

        arglist = [filename[0], filename[1],
                   '--murano-repo-url', murano_repo_url]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.assertEqual(2, self.package_mock.create.call_count)

        self.package_mock.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
            ], any_order=True,
        )


class TestBundleImport(TestPackage):
    def setUp(self):
        super(TestBundleImport, self).setUp()

        # Command to test
        self.cmd = osc_pkg.ImportBundle(self.app, None)

    @requests_mock.mock()
    def test_import_bundle_by_name(self, m):
        """Asserts bundle import calls packages create once for each pkg."""
        pkg1 = make_pkg({'FullName': 'first_app'})
        pkg2 = make_pkg({'FullName': 'second_app'})

        murano_repo_url = "http://127.0.0.1"

        m.get(murano_repo_url + '/apps/first_app.zip', body=pkg1)
        m.get(murano_repo_url + '/apps/second_app.1.0.zip',
              body=pkg2)
        s = io.StringIO()
        bundle_contents = {'Packages': [
            {'Name': 'first_app'},
            {'Name': 'second_app', 'Version': '1.0'}
        ]}
        json.dump(bundle_contents, s)
        s = io.BytesIO(s.getvalue().encode('ascii'))

        m.get(murano_repo_url + '/bundles/test_bundle.bundle',
              body=s)

        arglist = ["test_bundle", '--murano-repo-url', murano_repo_url]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.package_mock.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
            ], any_order=True,
        )

    @requests_mock.mock()
    def test_import_bundle_wrong_url(self, m):
        url = 'http://127.0.0.2/test_bundle.bundle'
        m.get(url, status_code=404)

        arglist = [url]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.assertFalse(self.package_mock.packages.create.called)

    @requests_mock.mock()
    def test_import_bundle_no_bundle(self, m):
        url = 'http://127.0.0.1/bundles/test_bundle.bundle'
        m.get(url, status_code=404)

        arglist = ["test_bundle"]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.assertFalse(self.package_mock.packages.create.called)

    @requests_mock.mock()
    def test_import_bundle_by_url(self, m):
        """Asserts bundle import calls packages create once for each pkg."""
        pkg1 = make_pkg({'FullName': 'first_app'})
        pkg2 = make_pkg({'FullName': 'second_app'})

        murano_repo_url = 'http://127.0.0.1'
        m.get(murano_repo_url + '/apps/first_app.zip', body=pkg1)
        m.get(murano_repo_url + '/apps/second_app.1.0.zip',
              body=pkg2)
        s = io.StringIO()
        bundle_contents = {'Packages': [
            {'Name': 'first_app'},
            {'Name': 'second_app', 'Version': '1.0'}
        ]}
        json.dump(bundle_contents, s)
        s = io.BytesIO(s.getvalue().encode('ascii'))

        url = 'http://127.0.0.2/test_bundle.bundle'
        m.get(url, body=s)

        arglist = [url, '--murano-repo-url', murano_repo_url]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.package_mock.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
            ], any_order=True,
        )

    @requests_mock.mock()
    def test_import_local_bundle(self, m):
        """Asserts local bundles are first searched locally."""
        tmp_dir = tempfile.mkdtemp()
        bundle_file = os.path.join(tmp_dir, 'bundle.bundle')
        with open(os.path.join(tmp_dir, 'bundle.bundle'), 'w') as f:

            bundle_contents = {'Packages': [
                {'Name': 'first_app'},
                {'Name': 'second_app', 'Version': '1.0'}
            ]}
            json.dump(bundle_contents, f)

        pkg1 = make_pkg({'FullName': 'first_app',
                         'Require': {'third_app': None}})
        pkg2 = make_pkg({'FullName': 'second_app'})
        pkg3 = make_pkg({'FullName': 'third_app'})
        with open(os.path.join(tmp_dir, 'first_app'), 'wb') as f:
            f.write(pkg1.read())
        with open(os.path.join(tmp_dir, 'third_app'), 'wb') as f:
            f.write(pkg3.read())

        murano_repo_url = "http://127.0.0.1"
        m.get(murano_repo_url + '/apps/first_app.zip',
              status_code=404)
        m.get(murano_repo_url + '/apps/second_app.1.0.zip',
              body=pkg2)
        m.get(murano_repo_url + '/apps/third_app.zip',
              status_code=404)

        arglist = [bundle_file, '--murano-repo-url', murano_repo_url]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.package_mock.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
                mock.call({'is_public': False}, {'third_app': mock.ANY}),
            ], any_order=True,
        )
        shutil.rmtree(tmp_dir)


class TestShowPackage(TestPackage):
    def setUp(self):
        super(TestShowPackage, self).setUp()

        # Command to test
        self.cmd = osc_pkg.ShowPackage(self.app, None)

    def test_package_show(self):
        arglist = ['fake']
        verifylist = [('id', 'fake')]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ('categories', 'class_definitions', 'description',
                            'enabled', 'fully_qualified_name', 'id',
                            'is_public', 'name', 'owner_id', 'tags', 'type')
        self.assertEqual(expected_columns, columns)

        self.package_mock.get.assert_called_with('fake')


class TestUpdatePackage(TestPackage):
    def setUp(self):
        super(TestUpdatePackage, self).setUp()

        self.package_mock.update.return_value = \
            (mock.MagicMock(), mock.MagicMock())

        # Command to test
        self.cmd = osc_pkg.UpdatePackage(self.app, None)

    def test_package_update(self):
        arglist = ['123', '--is-public', 'true']
        verifylist = [('id', '123'), ('is_public', True)]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self.cmd.take_action(parsed_args)

        self.package_mock.update.assert_called_with('123', {'is_public': True})

        arglist = ['123', '--enabled', 'true']
        verifylist = [('id', '123'), ('enabled', True)]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self.cmd.take_action(parsed_args)

        self.package_mock.update.assert_called_with('123', {'enabled': True})

        arglist = ['123', '--name', 'foo', '--description', 'bar']
        verifylist = [('id', '123'), ('name', 'foo'), ('description', 'bar')]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self.cmd.take_action(parsed_args)

        self.package_mock.update.assert_called_with(
            '123', {'name': 'foo', 'description': 'bar'})

        arglist = ['123', '--tags', 'foo']
        verifylist = [('id', '123'), ('tags', ['foo'])]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self.cmd.take_action(parsed_args)

        self.package_mock.update.assert_called_with(
            '123', {'tags': ['foo']})


class TestDownloadPackage(TestPackage):
    def setUp(self):
        super(TestDownloadPackage, self).setUp()

        self.package_mock.download.return_value = \
            b'This is a fake package buffer'

        # Command to test
        self.cmd = osc_pkg.DownloadPackage(self.app, None)

    def test_package_download(self):
        arglist = ['1234', '/tmp/foo.zip']
        verifylist = [('id', '1234'), ('filename', '/tmp/foo.zip')]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.cmd.take_action(parsed_args)

        self.package_mock.download.assert_called_with('1234')
