#    Copyright (c) 2013 Mirantis, Inc.
#
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
import re
import sys
import tempfile

import fixtures
from keystoneclient import fixture
from keystoneclient.fixture import v2 as ks_v2_fixture
from keystoneclient.fixture import v3 as ks_v3_fixture
import mock
import requests_mock
import six
from testtools import matchers

from muranoclient.openstack.common.apiclient import exceptions
import muranoclient.shell
from muranoclient.tests import base
from muranoclient.v1 import shell as v1_shell

FIXTURE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'fixture_data'))
# RESULT_PACKAGE = os.path.join(FIXTURE_DIR, 'test-app.zip')

FAKE_ENV = {'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where/v2.0'}

FAKE_ENV2 = {'OS_USERNAME': 'username',
             'OS_PASSWORD': 'password',
             'OS_TENANT_ID': 'tenant_id',
             'OS_AUTH_URL': 'http://no.where/v2.0'}

FAKE_ENV_v3 = {'OS_USERNAME': 'username',
               'OS_PASSWORD': 'password',
               'OS_TENANT_ID': 'tenant_id',
               'OS_USER_DOMAIN_NAME': 'domain_name',
               'OS_AUTH_URL': 'http://no.where/3'}


def _create_ver_list(versions):
    return {'versions': {'values': versions}}


class TestArgs(object):
    pass


class ShellTest(base.TestCaseShell):

    def make_env(self, exclude=None, fake_env=FAKE_ENV):
        env = dict((k, v) for k, v in fake_env.items() if k != exclude)
        self.useFixture(fixtures.MonkeyPatch('os.environ', env))


class ShellCommandTest(ShellTest):

    _msg_no_tenant_project = ('You must provide a project name or project'
                              ' id via --os-project-name, --os-project-id,'
                              ' env[OS_PROJECT_ID] or env[OS_PROJECT_NAME].'
                              ' You may use os-project and os-tenant'
                              ' interchangeably.',)

    def setUp(self):
        super(ShellCommandTest, self).setUp()

        def get_auth_endpoint(bound_self, args):
            return ('test', {})
        self.useFixture(fixtures.MonkeyPatch(
            'muranoclient.shell.MuranoShell._get_endpoint_and_kwargs',
            get_auth_endpoint))
        self.client = mock.MagicMock()

    def shell(self, argstr, exitcodes=(0,)):
        orig = sys.stdout
        orig_stderr = sys.stderr
        try:
            sys.stdout = six.StringIO()
            sys.stderr = six.StringIO()
            _shell = muranoclient.shell.MuranoShell()
            _shell.main(argstr.split())
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertIn(exc_value.code, exitcodes)
        finally:
            stdout = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig
            stderr = sys.stderr.getvalue()
            sys.stderr.close()
            sys.stderr = orig_stderr
        return (stdout, stderr)

    def register_keystone_discovery_fixture(self, mreq):
        v2_url = "http://no.where/v2.0"
        v2_version = fixture.V2Discovery(v2_url)
        mreq.register_uri('GET', v2_url, json=_create_ver_list([v2_version]),
                          status_code=200)

    def register_keystone_token_fixture(self, mreq):
        v2_token = ks_v2_fixture.Token(token_id='token')
        service = v2_token.add_service('application_catalog')
        service.add_endpoint('http://no.where', region='RegionOne')
        mreq.register_uri('POST',
                          'http://no.where/v2.0/tokens',
                          json=v2_token,
                          status_code=200)

    def test_help_unknown_command(self):
        self.assertRaises(exceptions.CommandError, self.shell, 'help foofoo')

    def test_help(self):
        required = [
            '.*?^usage: murano',
            '.*?^\s+package-create\s+Create an application package.',
            '.*?^See "murano help COMMAND" for help on a specific command',
        ]
        stdout, stderr = self.shell('help')
        for r in required:
            self.assertThat((stdout + stderr),
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_help_on_subcommand(self):
        required = [
            '.*?^usage: murano package-create',
            '.*?^Create an application package.',
        ]
        stdout, stderr = self.shell('help package-create')
        for r in required:
            self.assertThat((stdout + stderr),
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_help_no_options(self):
        required = [
            '.*?^usage: murano',
            '.*?^\s+package-create\s+Create an application package',
            '.*?^See "murano help COMMAND" for help on a specific command',
        ]
        stdout, stderr = self.shell('')
        for r in required:
            self.assertThat((stdout + stderr),
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_no_username(self):
        required = ('You must provide a username via either --os-username or '
                    'env[OS_USERNAME] or a token via --os-auth-token or '
                    'env[OS_AUTH_TOKEN]',)
        self.make_env(exclude='OS_USERNAME')
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    def test_no_tenant_name(self):
        required = self._msg_no_tenant_project
        self.make_env(exclude='OS_TENANT_NAME')
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    def test_no_tenant_id(self):
        required = self._msg_no_tenant_project
        self.make_env(exclude='OS_TENANT_ID', fake_env=FAKE_ENV2)
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    def test_no_auth_url(self):
        required = ('You must provide an auth url'
                    ' via either --os-auth-url or via env[OS_AUTH_URL]',)
        self.make_env(exclude='OS_AUTH_URL')
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    @mock.patch('muranoclient.v1.packages.PackageManager')
    @requests_mock.Mocker()
    def test_package_list(self, mock_package_manager, m_requests):
        self.client.packages = mock_package_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('package-list')
        self.client.packages.filter.assert_called_once_with(
            include_disabled=False)

    @mock.patch('muranoclient.v1.packages.PackageManager')
    @requests_mock.Mocker()
    def test_package_show(self, mock_package_manager, m_requests):
        self.client.packages = mock_package_manager()
        mock_package = mock.MagicMock()
        mock_package.class_definitions = ''
        mock_package.categories = ''
        mock_package.tags = ''
        mock_package.description = ''
        self.client.packages.get.return_value = mock_package
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('package-show 1234')
        self.client.packages.get.assert_called_once_with('1234')

    @mock.patch('muranoclient.v1.packages.PackageManager')
    @requests_mock.Mocker()
    def test_package_delete(self, mock_package_manager, m_requests):
        self.client.packages = mock_package_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('package-delete 1234')
        self.client.packages.delete.assert_called_once_with('1234')

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @requests_mock.Mocker()
    def test_environment_delete(self, mock_manager, m_requests):
        self.client.environments = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-delete env1 env2')
        self.client.environments.delete.assert_has_calls([
            mock.call('env1'), mock.call('env2')])

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @requests_mock.Mocker()
    def test_environment_rename(self, mock_manager, m_requests):
        self.client.environments = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-rename env-id new-name')
        self.client.environments.update.assert_called_once_with(
            'env-id', 'new-name')

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @requests_mock.Mocker()
    def test_environment_show(self, mock_manager, m_requests):
        self.client.environments = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-show env-id')
        self.client.environments.get.assert_called_once_with('env-id')

    @mock.patch('muranoclient.v1.deployments.DeploymentManager')
    @requests_mock.Mocker()
    def test_deployments_show(self, mock_manager, m_requests):
        self.client.deployments = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('deployment-list env-id')
        self.client.deployments.list.assert_called_once_with('env-id')


class ShellPackagesOperations(ShellCommandTest):
    def tearDown(self):
        super(ShellPackagesOperations, self).tearDown()

    @requests_mock.Mocker()
    def test_create_hot_based_package(self, m_requests):
        self.useFixture(fixtures.MonkeyPatch(
            'muranoclient.v1.client.Client', mock.MagicMock))
        heat_template = os.path.join(FIXTURE_DIR, 'heat-template.yaml')
        logo = os.path.join(FIXTURE_DIR, 'logo.png')
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name
            c = "package-create --template={0} --output={1} -l={2}".format(
                heat_template, RESULT_PACKAGE, logo)
            stdout, stderr = self.shell(c)
            matchers.MatchesRegex((stdout + stderr),
                                  "Application package "
                                  "is available at {0}".format(RESULT_PACKAGE))

    @requests_mock.Mocker()
    def test_create_mpl_package(self, m_requests):
        self.useFixture(fixtures.MonkeyPatch(
            'muranoclient.v1.client.Client', mock.MagicMock))
        classes_dir = os.path.join(FIXTURE_DIR, 'test-app', 'Classes')
        resources_dir = os.path.join(FIXTURE_DIR, 'test-app', 'Resources')
        ui = os.path.join(FIXTURE_DIR, 'test-app', 'ui.yaml')
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name
            stdout, stderr = self.shell(
                "package-create  -c={0} -r={1} -u={2} -o={3}".format(
                    classes_dir, resources_dir, ui, RESULT_PACKAGE))
            matchers.MatchesRegex((stdout + stderr),
                                  "Application package "
                                  "is available at {0}".format(RESULT_PACKAGE))

    def test_package_import(self):
        args = TestArgs()
        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name
            args.filename = RESULT_PACKAGE
            args.categories = ['Cat1', 'Cat2 with space']

            v1_shell.do_package_import(self.client, args)

            self.client.packages.create.assert_called_once_with(
                {'categories': ['Cat1', 'Cat2 with space']},
                ((RESULT_PACKAGE, mock.ANY),)
            )

    def test_package_import_no_categories(self):
        args = TestArgs()
        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name

            args.filename = RESULT_PACKAGE
            args.categories = None

            v1_shell.do_package_import(self.client, args)

            self.client.packages.create.assert_called_once_with(
                None,
                ((RESULT_PACKAGE, mock.ANY),)
            )

    def test_package_import_wrong_file(self):
        args = TestArgs()
        args.filename = '/home/this/path/does/not/exist'
        args.categories = None

        self.assertRaises(IOError,
                          v1_shell.do_package_import, self.client, args)


class ShellPackagesOperationsV3(ShellPackagesOperations):
    def make_env(self, exclude=None, fake_env=FAKE_ENV):
        if 'OS_AUTH_URL' in fake_env:
            fake_env.update({'OS_AUTH_URL': 'http://no.where/v3'})
        env = dict((k, v) for k, v in fake_env.items() if k != exclude)
        self.useFixture(fixtures.MonkeyPatch('os.environ', env))

    def register_keystone_discovery_fixture(self, mreq):
        v3_url = "http://no.where/v3"
        v3_version = fixture.V3Discovery(v3_url)
        mreq.register_uri('GET', v3_url, json=_create_ver_list([v3_version]),
                          status_code=200)

    def register_keystone_token_fixture(self, mreq):
        v3_token = ks_v3_fixture.Token()
        service = v3_token.add_service('application_catalog')
        service.add_standard_endpoints(public='http://no.where')
        mreq.register_uri('POST',
                          'http://no.where/v3/auth/tokens',
                          json=v3_token,
                          headers={'X-Subject-Token': 'tokenid'},
                          status_code=200)
